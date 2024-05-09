using System;
using System.Collections.ObjectModel;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using DataMonClient.Panels;
using DevExpress.Xpf.Bars;
using DevExpress.Xpf.Charts;
using DevExpress.Xpf.Editors;
using DvnDraw;
using NetCommon.Var;
using Range = DevExpress.Xpf.Charts.Range;

namespace DataMonClient.Controls
{
    public partial class CtrlTrendWPF : UserControl
    {
        private const byte TREND_ID = 31;

        private UserNetApi _userNetApi;
        private long _timeRange;
        private long _timeInterval;
        private long _shift;
        private readonly object _trendLock = new object();
        private readonly System.Windows.Threading.DispatcherTimer _trendTimer;
        private readonly TrendSeriesManager _seriesManager;

        public CtrlTrendWPF(UserNetApi userNetApi)
        {
            InitializeComponent();
            _userNetApi = userNetApi;

            _trendTimer = new System.Windows.Threading.DispatcherTimer();
            _seriesManager = new TrendSeriesManager(dcTrendWPF);

            dcTrendWPF.AllowDrop = true;
            dcTrendWPF.PreviewDragOver += HandlePreviewDragOver;
            dcTrendWPF.Drop += HandleDrop;
        }

        public void LoadControl(PanelTrendWPF panelTrendWPF)
        {
            _timeRange = GetRange();
            _timeInterval = GetInterval();
            beiTime.EditValue = DateTime.Now;

            _userNetApi.EvtAcValuesPlot += new UserNetImpl.DgAcValuesPlot(TrendValues);
            _trendTimer.Tick += new EventHandler(AutoTrendProcess);
            _trendTimer.Interval = TimeSpan.FromSeconds(1);
            _trendTimer.Start();
        }

        public void CloseControl()
        {
            _trendTimer.Stop();
            _trendTimer.Tick -= new EventHandler(AutoTrendProcess);
            _userNetApi.EvtAcValuesPlot -= new UserNetImpl.DgAcValuesPlot(TrendValues);

            _seriesManager.ClearAllSeries();
        }

        private void RefreshTrend()
        {
            var endTime = ((DateTime)beiTime.EditValue).ToFileTime();
            var startTime = endTime - _timeRange;

            _seriesManager.SetTimeRange(startTime, endTime);
            RetrieveTrend(startTime, endTime, _timeInterval);
        }

        private void RetrieveTrend(long startTime, long endTime, long interval)
        {
            var tagIds = _seriesManager.GetTagIds();

            if (tagIds.Any())
            {
                _userNetApi.GetAcValuesTrend(
                    TREND_ID, tagIds, startTime, endTime, interval,
                    GetInterpolationMode(), null, UserNet.FilterMode.calculate);
            }
        }

        private void TrendValues(uint trendId, long startTime, long endTime, long interval, uint[] tagIds, Variant[,] values)
        {
            if (trendId != TREND_ID) return;

            Application.Current.Dispatcher.BeginInvoke(new Action(() => UpdateTrendData(startTime, endTime, interval, tagIds, values)));
        }

        private void UpdateTrendData(long startTime, long endTime, long interval, uint[] tagIds, Variant[,] values)
        {
            try
            {
                for (int tagIndex = 0; tagIndex < values.GetLength(0); tagIndex++)
                {
                    var tagId = tagIds[tagIndex];
                    var series = _seriesManager.GetSeriesById(tagId);

                    if (series == null) continue;

                    series.ClearPoints();

                    for (int i = 0; i < values.GetLength(1); i++)
                    {
                        var value = values[tagIndex, i];
                        if (!value.IsQualityBad)
                        {
                            var timestamp = value.TimestampToDateTime();
                            var point = new TrendDataPoint(timestamp, value.ToReal64());
                            series.AddPoint(point);
                        }
                    }
                }

                _seriesManager.UpdateAxis();
            }
            catch (Exception ex)
            {
                // 예외 정보 로깅
                Logger.Error($"트렌드 데이터 처리 중 오류 발생: {ex}");
                MessageBox.Show("트렌드 데이터를 처리하는 중 오류가 발생했습니다. 관리자에게 문의하세요.", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void HandlePreviewDragOver(object sender, DragEventArgs e)
        {
            if (e.Data.GetDataPresent(DataFormats.Text))
            {
                e.Effects = DragDropEffects.Copy;
            }
            else
            {
                e.Effects = DragDropEffects.None;
            }

            e.Handled = true;
        }

        private void HandleDrop(object sender, DragEventArgs e)
        {
            var text = e.Data.GetData(DataFormats.Text) as string;
            var tagNames = text?.Split(',') ?? new string[0];

            foreach (var name in tagNames)
            {
                if (string.IsNullOrWhiteSpace(name)) continue;

                if (_userNetApi.GetTagInfo(name, out uint tagId, out _, out _, out double min, out double max, out string unit))
                {
                    var series = new TrendSeries(tagId, name, min, max, unit);
                    _seriesManager.AddSeries(series);
                }
            }

            RefreshTrend();
        }

        private void AutoTrendProcess(object sender, EventArgs e)
        {
            var now = DateTime.Now;
            var endTime = now.ToFileTime() + _shift;
            var startTime = endTime - _timeRange;

            beiTime.EditValue = now;
            RetrieveTrend(startTime, endTime, _timeInterval);
        }

        private UserNet.IpoMode GetInterpolationMode()
        {
            if (bciIpoAvg.IsChecked == true) return UserNet.IpoMode.avg;
            if (bciIpoMin.IsChecked == true) return UserNet.IpoMode.min;
            if (bciIpoMax.IsChecked == true) return UserNet.IpoMode.max;

            return UserNet.IpoMode.raw;
        }

        private long GetRange()
        {
            switch (beicbRange.EditValue.ToString())
            {
                case "1 minute": return TimeRange.OneMinute.ToFileTime();
                case "10 minutes": return TimeRange.TenMinutes.ToFileTime();
                case "1 hour": return TimeRange.OneHour.ToFileTime();
                case "1 day": return TimeRange.OneDay.ToFileTime();
                case "1 week": return TimeRange.OneWeek.ToFileTime();
                case "1 month": return TimeRange.OneMonth.ToFileTime();
                case "1 year": return TimeRange.OneYear.ToFileTime();
                default: return TimeRange.TenMinutes.ToFileTime();
            }
        }

        private long GetInterval()
        {
            switch (beicbInterval.EditValue.ToString())
            {
                case "1 ms": return TimeInterval.OneMillisecond.ToFileTime();
                case "10 ms": return TimeInterval.TenMilliseconds.ToFileTime();
                case "100 ms": return TimeInterval.HundredMilliseconds.ToFileTime();
                case "1 second": return TimeInterval.OneSecond.ToFileTime();
                case "1 minute": return TimeInterval.OneMinute.ToFileTime();
                case "1 hour": return TimeInterval.OneHour.ToFileTime();
                case "1 day": return TimeInterval.OneDay.ToFileTime();
                default: return TimeInterval.OneSecond.ToFileTime();
            }
        }

        private void BeiTime_EditValueChanged(object sender, EditValueChangedEventArgs e)
        {
            if (e.NewValue is DateTime time)
            {
                var endTime = time.ToFileTime();
                var startTime = endTime - _timeRange;
                RetrieveTrend(startTime, endTime, _timeInterval);
            }
        }

        private void BbiPlay_ItemClick(object sender, ItemClickEventArgs e)
        {
            lock (_trendLock)
            {
                bbiPlay.IsEnabled = false;
                bbiStop.IsEnabled = true;
                _trendTimer.Start();
            }
        }

        private void BbiStop_ItemClick(object sender, ItemClickEventArgs e)
        {
            lock (_trendLock)
            {
                bbiPlay.IsEnabled = true;
                bbiStop.IsEnabled = false;
                _trendTimer.Stop();
                _shift = 0;
            }
        }

        private void BciIpoAvg_ItemClick(object sender, ItemClickEventArgs e)
        {
            CheckInterpolationMode(Interpolation.Average);
        }

        private void BciIpoMin_ItemClick(object sender, ItemClickEventArgs e)
        {
            CheckInterpolationMode(Interpolation.Minimum);
        }

        private void BciIpoMax_ItemClick(object sender, ItemClickEventArgs e)
        {
            CheckInterpolationMode(Interpolation.Maximum);
        }

        private void BciIpoRaw_ItemClick(object sender, ItemClickEventArgs e)
        {
            CheckInterpolationMode(Interpolation.Raw);
        }

        private void CheckInterpolationMode(Interpolation mode)
        {
            bciIpoAvg.IsChecked = (mode == Interpolation.Average);
            bciIpoMin.IsChecked = (mode == Interpolation.Minimum);
            bciIpoMax.IsChecked = (mode == Interpolation.Maximum);
            bciIpoRaw.IsChecked = (mode == Interpolation.Raw);

            RefreshTrend();
        }

        private void UpdateAxisMode(AxisMode mode)
        {
            bbiAxisModeSingle.IsChecked = (mode == AxisMode.Single);
            bbiAxisModeMultiple.IsChecked = (mode == AxisMode.Multiple);
            bbiAxisModeMinMax.IsChecked = (mode == AxisMode.MinMax);

            _seriesManager.AxisMode = mode;
            _seriesManager.UpdateAxis();
        }

        private void BbiAxisModeSingle_ItemClick(object sender, ItemClickEventArgs e)
        {
            UpdateAxisMode(AxisMode.Single);
        }

        private void BbiAxisModeMultiple_ItemClick(object sender, ItemClickEventArgs e)
        {
            UpdateAxisMode(AxisMode.Multiple);
        }

        private void BbiAxisModeMinMax_ItemClick(object sender, ItemClickEventArgs e)
        {
            UpdateAxisMode(AxisMode.MinMax);
        }
    }

    internal class TrendSeries
    {
        public uint TagId { get; }
        public string Name { get; }
        public double MinValue { get; }
        public double MaxValue { get; }
        public string Unit { get; }
        public LineSeries2D ChartSeries { get; }

        public TrendSeries(uint tagId, string name, double min, double max, string unit)
        {
            TagId = tagId;
            Name = name;
            MinValue = min;
            MaxValue = max;
            Unit = unit;
            ChartSeries = new LineSeries2D
            {
                ArgumentScaleType = ScaleType.DateTime,
                ValueDataMember = nameof(TrendDataPoint.Value),
                ArgumentDataMember = nameof(TrendDataPoint.Timestamp)
            };
        }

        public void AddPoint(TrendDataPoint point)
        {
            //ChartSeries.Points.Add(point);
        }

        public void ClearPoints()
        {
            ChartSeries.Points.Clear();
        }
    }

    internal class TrendDataPoint
    {
        public DateTime Timestamp { get; set; }
        public double Value { get; set; }

        public TrendDataPoint(DateTime time, double value)
        {
            Timestamp = time;
            Value = value;
        }
    }

    internal class TrendSeriesManager
    {
        private readonly ChartControl _chart;
        private readonly ObservableCollection<TrendSeries> _seriesList;

        public AxisMode AxisMode { get; set; }

        public TrendSeriesManager(ChartControl chart)
        {
            _chart = chart;
            _seriesList = new ObservableCollection<TrendSeries>();

            AxisMode = AxisMode.Single;
            _chart.Diagram = new XYDiagram2D();
        }

        public TrendSeries GetSeriesById(uint tagId)
        {
            return _seriesList.FirstOrDefault(s => s.TagId == tagId);
        }

        public void AddSeries(TrendSeries series)
        {
            _seriesList.Add(series);
            _chart.Diagram.Series.Add(series.ChartSeries);
        }

        public void RemoveSeries(TrendSeries series)
        {
            _seriesList.Remove(series);
            _chart.Diagram.Series.Remove(series.ChartSeries);
        }

        public void ClearAllSeries()
        {
            _seriesList.Clear();
            _chart.Diagram.Series.Clear();
        }

        public void SetTimeRange(long startTime, long endTime)
        {
            //
            _chart.Diagram.AxisX.Range = new Range
            {
                //
                MinValue = startTime.ToOADate(),
                //
                MaxValue = endTime.ToOADate()
            };
        }

        public uint[] GetTagIds() => _seriesList.Select(s => s.TagId).ToArray();

        public void UpdateAxis()
        {

            //var axisX = (XYDiagram2D)_chart.Diagram.AxisX;
            //axisX.DateTimeScaleOptions.MeasureUnit = DateTimeMeasureUnit.Second;
            //axisX.Label.TextPattern = "{A:yyyy-MM-dd HH:mm:ss}";

            var axisX = ((XYDiagram2D)_chart.Diagram).AxisX;
            var axisY = ((XYDiagram2D)_chart.Diagram).AxisY;
            axisX.DateTimeScaleOptions = new ManualDateTimeScaleOptions { MeasureUnit = DateTimeMeasureUnit.Second };
            axisX.Label.TextPattern = "{A:yyyy-MM-dd HH:mm:ss}";

            switch (AxisMode)
            {
                case AxisMode.Single:
                    axisY.NumericScaleOptions.AutoGrid = true;//
                    break;
                case AxisMode.Multiple:
                    foreach (var series in _seriesList)
                    {
                        series.ChartSeries.AxisY = new AxisY2D
                        {
                            Title = new AxisTitle { Text = series.Name },//
                            Label = { TextPattern = "{V} " + series.Unit }
                        };
                    }
                    break;
                case AxisMode.MinMax:
                    var minValue = _seriesList.Min(s => s.MinValue);
                    var maxValue = _seriesList.Max(s => s.MaxValue);
                    _chart.Diagram.AxisY.WholeRange = new Range { MinValue = minValue, MaxValue = maxValue };//
                    break;
            }
        }
    }

    internal enum TimeRange
    {
        OneMinute = 60,
        TenMinutes = 600,
        OneHour = 3600,
        OneDay = 86400,
        OneWeek = 604800, OneMonth = 2592000,
        OneYear = 31536000
    }

    internal enum TimeInterval
    {
        OneMillisecond = 1,
        TenMilliseconds = 10,
        HundredMilliseconds = 100,
        OneSecond = 1000,
        OneMinute = 60000,
        OneHour = 3600000,
        OneDay = 86400000
    }

    internal enum Interpolation
    {
        Raw,
        Average,
        Minimum,
        Maximum
    }

    internal enum AxisMode
    {
        Single,
        Multiple,
        MinMax
    }

    internal static class TimeExtensions
    {
        public static long ToFileTime(this TimeRange range)
        {
            return ((long)range) * 10_000_000;
        }

        public static long ToFileTime(this TimeInterval interval)
        {
            return ((long)interval) * 10_000;
        }

        public static DateTime TimestampToDateTime(this Variant value)
        {
            return DateTime.FromFileTime(value.Timestamp);
        }
    }

    internal static class Logger
    {
        public static void Error(string message)
        {
            // 실제 로깅 구현부 호출
            System.Diagnostics.Debug.WriteLine($"[ERROR] {message}");
        }
    }
}
