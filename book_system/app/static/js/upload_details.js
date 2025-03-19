console.log('=== upload_details.js 开始加载 ===');

// 检查依赖项
if (typeof jQuery === 'undefined') {
    console.error('jQuery 未加载');
} else {
    console.log('jQuery 已加载');
}

if (typeof echarts === 'undefined') {
    console.error('echarts 未加载');
} else {
    console.log('echarts 已加载');
}

// 词云图表初始化
window.initUploadWordCloud = function(containerId, wordCloudData) {
    var container = document.getElementById(containerId);
    if (!container) {
        console.error('找不到词云容器:', containerId);
        return;
    }

    try {
        var wordCloudChart = echarts.init(container);
        
        var option = {
            tooltip: {
                show: true,
                formatter: function(params) {
                    return params.data.name + ': ' + Math.round(params.data.value);
                }
            },
            series: [{
                type: 'wordCloud',
                shape: 'circle',
                width: '90%',
                height: '90%',
                sizeRange: [14, 80],
                rotationRange: [-45, 45],
                rotationStep: 45,
                gridSize: 8,
                drawOutOfBound: false,
                layoutAnimation: true,
                textStyle: {
                    fontFamily: 'sans-serif',
                    fontWeight: 'bold',
                    color: function () {
                        return 'rgb(' + [
                            Math.round(Math.random() * 160),
                            Math.round(Math.random() * 160),
                            Math.round(Math.random() * 160)
                        ].join(',') + ')';
                    }
                },
                emphasis: {
                    focus: 'self',
                    textStyle: {
                        shadowBlur: 10,
                        shadowColor: '#333'
                    }
                },
                data: wordCloudData
            }]
        };
        
        wordCloudChart.setOption(option);
        
        // 监听窗口大小变化
        window.addEventListener('resize', function() {
            wordCloudChart.resize();
        });
        
        return wordCloudChart;
        
    } catch (error) {
        console.error('词云初始化失败:', error);
        console.error('错误堆栈:', error.stack);
    }
};

// 页面初始化
layui.use(['layer'], function(){
    var $ = layui.jquery;
    var layer = layui.layer;
    
    // 页面加载完成后初始化词云
    $(window).on('load', function() {
        console.log('页面加载完成，准备初始化词云');
        setTimeout(function() {
            window.initUploadWordCloud('wordcloud', window.wordCloudData || []);
        }, 300);
    });
});