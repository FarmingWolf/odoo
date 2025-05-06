// 动态加载天地图地图API
function loadTDTIOMapScript(apiKey, callback) {
    const script = document.createElement('script');
    script.src = `https://api.tianditu.gov.cn/api?v=4.0&tk=${apiKey}`;
    script.async = true;

    // 将AK存储在全局变量中
    window.tiandituMapAK = apiKey;
    // 天地图API加载完成后再执行回调
    script.onload = function() {
        console.log("天地图API加载完成");
        if (typeof window[callback] === 'function') {
            window[callback]();
        }
    };
    document.head.appendChild(script);
}

// 在页面加载完成后初始化地图
document.addEventListener('DOMContentLoaded', function () {
    // 从URL参数获取经纬度
    const urlParams = new URLSearchParams(window.location.search);
    const tgt_lat = parseFloat(urlParams.get('lat'));
    const tgt_lon = parseFloat(urlParams.get('lon'));

    if (isNaN(tgt_lat) || isNaN(tgt_lon)) {
        console.error('经纬度参数无效');
        return;
    }
    // 从Controller获取天地图地图AK
    fetch('/estate_slides/tdt_map/get_ak')
        .then(response => response.json())
        .then(data => {
            const tdtMapAK = data.ak; // 获取天地图地图AK
            if (!tdtMapAK) {
                console.error('天地图地图AK未配置');
                return;
            } else {
                console.log("天地图地图AK返回OK")
            }

            // 加载天地图地图API
            loadTDTIOMapScript(tdtMapAK, 'initCheckInOutTDTMap');

            // 定义回调函数
            window.initCheckInOutTDTMap = function () {
                if (typeof T === 'undefined') {
                    console.info('天地图地图API未成功加载');
                    return;
                } else {
                    console.log('天地图地图API已成功加载');
                }

                // 获取地图容器
                const mapContainer = document.getElementById('et-check-i-o-tdt-map-container');
                if (!mapContainer) {
                    console.info('et-check-i-o-tdt-map-container not fund!');
                    return;
                }

                const zoom = 18
                // 初始化地图
                const map = new T.Map("et-check-i-o-tdt-map-container", {
                    projection: 'EPSG:4326'
                });

                const point = new T.LngLat(tgt_lon, tgt_lat);
                map.centerAndZoom(point, zoom);
                map.enableScrollWheelZoom(true);

                const markerIcon = new T.Icon({
                    iconUrl: 'https://api.tianditu.gov.cn/img/map/marker.png',
                    iconSize: new T.Point(25, 25),
                    iconAnchor: new T.Point(12, 25)
                });
                const mapMarker = new T.Marker(point, {icon: markerIcon});
                map.addOverLay(mapMarker);

            };
        })
        .catch(error => {
            console.error('获取天地图地图AK失败:', error);
        });
});
