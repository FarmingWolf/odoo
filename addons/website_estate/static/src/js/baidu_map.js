// 动态加载百度地图API
function loadBaiduMapScript(apiKey, callback) {
    const script = document.createElement('script');
    script.src = `https://api.map.baidu.com/api?v=3.0&ak=${apiKey}&callback=${callback}`;
    script.async = true; // 异步加载
    document.head.appendChild(script);
}

// 在页面加载完成后初始化地图
document.addEventListener('DOMContentLoaded', function () {
    // 从Controller获取百度地图AK
    fetch('/estate_slides/baidu_map/get_ak')
        .then(response => response.json())
        .then(data => {
            const baiduMapAK = data.ak; // 获取百度地图AK
            if (!baiduMapAK) {
                console.error('百度地图AK未配置');
                return;
            } else {
                console.log("百度地图AK返回OK")
            }

            // 加载百度地图API
            loadBaiduMapScript(baiduMapAK, 'initBaiduMap');

            // 定义回调函数
            window.initBaiduMap = function () {
                if (typeof BMap === 'undefined') {
                    console.error('百度地图API未成功加载');
                    return;
                } else {
                    console.log('百度地图API已成功加载');
                }
                // 初始化地图
                const map = new BMap.Map("baidu-map-container");
                // console.log('百度地图map已成功初始化');
                // const point = new BMap.Point(116.404, 39.915); // 默认中心点 天安门故宫
                const point = new BMap.Point(116.590, 39.896); // 默认中心点491Park
                map.centerAndZoom(point, 15); // 初始化地图，设置中心点坐标和地图级别
                // 启用滚轮缩放
                map.enableScrollWheelZoom(true);
                // //     // 监听地图点击事件
                // map.addEventListener('click', function (e) {
                //     // 获取点击点的经纬度
                //     const latitude = e.point.lat; // 纬度
                //     const longitude = e.point.lng; // 经度
                //
                //     // 在控制台输出经纬度
                //     console.log(`纬度: ${latitude}, 经度: ${longitude}`);
                //
                //     // 可选：在地图上显示点击点的标记
                //     const marker = new BMap.Marker(e.point);
                //     map.addOverlay(marker);
                //
                //     // 可选：显示信息窗口
                //     const infoWindow = new BMap.InfoWindow(`纬度: ${latitude}, 经度: ${longitude}`);
                //     map.openInfoWindow(infoWindow, e.point);
                // });

                // 从Controller获取点位信息
                fetch('/estate_slides/baidu_map/get_markers')
                    .then(response => response.json())
                    .then(markers => {
                        // 动态添加标记
                        console.log("markers", markers)
                        markers.forEach(marker => {
                            const point = new BMap.Point(marker.longitude, marker.latitude);
                            const mapMarker = new BMap.Marker(point);
                            map.addOverlay(mapMarker);

                            // 添加信息窗口（可选）
                            const infoWindow = new BMap.InfoWindow(marker.name);
                            mapMarker.addEventListener('click', function () {
                                this.openInfoWindow(infoWindow);
                            });
                        });
                    })
                    .catch(error => {
                        console.error('获取点位信息失败:', error);
                    });
            };
        })
        .catch(error => {
            console.error('获取百度地图AK失败:', error);
        });
});
