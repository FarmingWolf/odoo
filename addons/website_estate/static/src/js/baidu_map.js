// 动态加载百度地图API
function loadBaiduMapScript(apiKey, callback) {
    const script = document.createElement('script');
    script.src = `https://api.map.baidu.com/api?v=3.0&ak=${apiKey}&callback=${callback}`;
    script.async = true; // 异步加载
    document.head.appendChild(script);
}

function getCenterMarker(markers) {
    if (markers.length <= 0) {
        return null;
    }
    if (markers.length === 1) {
        return markers[0];
    }
    // 1. 提取所有点的经纬度
    const lngs = markers.map(marker => marker.longitude);
    const lats = markers.map(marker => marker.latitude);

    const maxLng = Math.max(...lngs);
    const minLng = Math.min(...lngs);
    const maxLat = Math.max(...lats);
    const minLat = Math.min(...lats);

    const medianLng = (maxLng + minLng) / 2;
    const medianLat = (maxLat + minLat) / 2;

    // 4. 找到距离中位点最近的点
    let closestMarker = markers[0];
    let minDistance = Infinity;

    markers.forEach(marker => {
        const distance = Math.sqrt(
            Math.pow(marker.longitude - medianLng, 2) +
            Math.pow(marker.latitude - medianLat, 2)
        );

        if (distance < minDistance) {
            minDistance = distance;
            closestMarker = marker;
        }
    });

    // 输出结果
    console.log('中位点:', closestMarker);
    console.log('中位点经度:', closestMarker.longitude);
    console.log('中位点纬度:', closestMarker.latitude);
    return closestMarker;
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
                    console.info('百度地图API未成功加载');
                    return;
                } else {
                    console.log('百度地图API已成功加载');
                }
                const zoom = 18
                // 初始化地图
                const map = new BMap.Map("baidu-map-container");
                // console.log('百度地图map已成功初始化');
                // const point = new BMap.Point(116.404, 39.915); // 默认中心点 天安门故宫
                const point = new BMap.Point(116.590, 39.896); // 默认中心点491Park
                map.centerAndZoom(point, zoom); // 初始化地图，设置中心点坐标和地图级别
                // 启用滚轮缩放
                map.enableScrollWheelZoom(true);

                // 从Controller获取点位信息
                fetch('/estate_slides/baidu_map/get_markers')
                    .then(response => response.json())
                    .then(markers => {
                        // 获取中位点
                        const centerMarker = getCenterMarker(markers);
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
                        if (typeof centerMarker === "undefined") {
                        } else {
                            const point = new BMap.Point(centerMarker.longitude, centerMarker.latitude);
                            map.centerAndZoom(point, zoom);
                        }
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
