
void TrendValues2(uint trendId, long startTime, long endTime, long interval, UInt32[] tagIds, Variant[,] values)
{
    int numSeries = values.GetLength(0);
    int numPoints = values.GetLength(1);

    // 기존 시리즈 수와 새로운 시리즈 수 비교
    int numExistingSeries = plotSeries.Count;
    int numNewSeries = numSeries - numExistingSeries;

    // 새로운 시리즈 생성
    for (int i = 0; i < numNewSeries; i++)
    {
        var series = new LineScatterSeries2D();
        series.DisplayName = $"Series {numExistingSeries + i + 1}";
        series.MarkerVisible = true;
        plotSeries.Add(series);
        dcTrendWPF.Diagram.Series.Add(series);
    }

    // 기존 시리즈의 포인트 삭제
    for (int i = 0; i < numExistingSeries; i++)
    {
        var series = (LineScatterSeries2D)plotSeries[i];
        series.Points.Clear();
    }

    // 시리즈에 포인트 추가
    for (int i = 0; i < numSeries; i++)
    {
        var series = (LineScatterSeries2D)plotSeries[i];
        for (int j = 0; j < numPoints; j++)
        {
            Variant xValue = values[i, j];
            Variant yValue = i == 0 ? new Variant(j) : values[i, j];

            if (!xValue.IsQualityBad && !yValue.IsQualityBad)
            {
                series.Points.Add(new SeriesPoint(xValue.ToReal64(), yValue.ToReal64()));
            }
        }
    }

    // X축을 첫번째 시리즈의 값으로 설정
    ((XYDiagram2D)dcTrendWPF.Diagram).AxisX.DateTimeScaleOptions = null;
    ((XYDiagram2D)dcTrendWPF.Diagram).AxisX.Label.TextPattern = "{V}";

    UpdateAxisMode();
}
