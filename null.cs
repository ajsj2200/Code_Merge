
case AxisMode.MinMax:
    // Min-Max 모드 (트레이스별 축, 눈금 숨김)
    foreach (var tp in tpManager.TraceProperties)
    {
        var series = (XYSeries2D)tp.Series;

        // 트레이스 전용 Y축 생성
        var axisY = new SecondaryAxisY2D();
        axisY.Alignment = series.AxisYAlignment;
        axisY.Visible = false; // 눈금 숨김
        diagram.SecondaryAxesY.Add(axisY);
        series.AxisY = axisY;
        
        // 트레이스의 min, max 값 표시
        var minLabel = new AxisLabel();
        minLabel.Angle = 0;
        minLabel.TextPattern = $"{tp.MinValue:F2}";
        minLabel.Alignment = AxisLabelAlignment.Far;  
        minLabel.Style = new Style(typeof(AxisLabel));
        minLabel.Style.Setters.Add(new Setter(AxisLabel.ForegroundProperty, series.Brush));
        axisY.CustomLabels.Add(minLabel);

        var maxLabel = new AxisLabel();
        maxLabel.Angle = 0;
        maxLabel.TextPattern = $"{tp.MaxValue:F2}";
        maxLabel.Alignment = AxisLabelAlignment.Near;
        maxLabel.Style = new Style(typeof(AxisLabel));
        maxLabel.Style.Setters.Add(new Setter(AxisLabel.ForegroundProperty, series.Brush));
        axisY.CustomLabels.Add(maxLabel);

        axisY.SetRange(new Range(tp.MinValue, tp.MaxValue));
    }
    break;

변경 사항을 설명 드리면:

1. 각 트레이스마다 새로운 SecondaryAxisY2D를 생성합니다. 이 축은 Visible을 false로 설정하여 눈금을 숨깁니다.

2. 트레이스의 AxisY를 해당 축으로 지정합니다. 트레이스별로 독립적인 Y축을 가지게 됩니다.

3. 각 축마다 CustomLabels를 추가하여 최소값과 최대값을 표시합니다.
   - 최소값 레이블은 Alignment를 Far로 설정하여 아래쪽에 표시 
   - 최대값 레이블은 Alignment를 Near로 설정하여 위쪽에 표시
   - 레이블의 포그라운드 색상을 해당 트레이스의 Brush와 동일하게 설정

4. 축의 SetRange 메소드로 최소, 최대 범위를 설정합니다. 
   
이렇게 하면 트레이스마다 독립적인 Y축을 가지면서, 축의 눈금은 보이지 않고 최소/최대값만 트레이스 색상으로 양 끝에 표시됩니다.

각 트레이스가 개별 축을 사용하므로 multi-axis처럼 보이지만, 실제로는 축의 눈금이 보이지 않는 min-max 전용 모드가 구현됩니다.

의도하신 바를 제대로 반영했는지 확인 부탁드립니다. 미진한 부분이 있다면 말씀해 주세요.
</result>