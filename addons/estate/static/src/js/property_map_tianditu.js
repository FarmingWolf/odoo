// 动态加载天地图地图API
function loadPropertiesTiandituMapScript(apiKey, callback) {
    console.log("enter loadPropertiesTiandituMapScript")
    // 获取地图容器
    const mapContainer = document.getElementById('properties_tianditu_map_container');
    if (!mapContainer) {
        console.info('properties_tianditu_map_container无地图容器页面不加载API');
        return;
    }
    // 将AK存储在全局变量中
    window.tiandituMapAK = apiKey;

    // 先加载天地图API的核心JS
    const script = document.createElement('script');
    script.src = `https://api.tianditu.gov.cn/api?v=4.0&tk=${apiKey}`;
    script.async = true;

    // 天地图API加载完成后再执行回调
    script.onload = function() {
        console.log("天地图API加载完成");
        if (typeof window[callback] === 'function') {
            window[callback]();
        }
    };

    document.head.appendChild(script);
}

// 初始化地图
async function initPropertiesTiandituMap() {
    console.log("enter initPropertiesTiandituMap");

    // 检查天地图API是否加载成功
    if (typeof T === 'undefined') {
        console.log('天地图API未成功加载');
        return;
    }

    let map = new T.Map("properties_tianditu_map_container", {
                projection: 'EPSG:4326'
            });
    if (typeof map === 'undefined') {
        console.log('properties_tianditu_map_container没找到……');
        return;
    }

    // 获取地图容器
    const mapContainer = document.getElementById('properties_tianditu_map_container');
    if (!mapContainer) {
        console.info('properties_tianditu_map_container地图容器未找到');
        return;
    }

    fetch(`/estate/tianditu_map/get_company_loc`, {
        method: 'GET',
        headers: {
            'Accept': 'application/json',
        },
    })
        .then(response => response.json())
        .then(company_marker => {
            company_marker.forEach(marker => {
                const point = new T.LngLat(marker.longitude, marker.latitude);
                console.log("longitude", marker.longitude, "latitude", marker.latitude)
                map.centerAndZoom(point, 18); // 初始化地图，设置中心点坐标和地图级别
                map.enableScrollWheelZoom(true); // 启用滚轮缩放
            });
        })
            .catch(error => {
                console.error('获取点位信息失败:', error);
            });

    // 从Controller获取点位信息
    await fetch(`/estate/tianditu_map/get_all_properties`, {
        method: 'GET',
        headers: {
            'Accept': 'application/json',
        },
    })
        .then(response => response.json())
        .then(property_markers => {
            console.log("property_markers", property_markers);
            let setCenter = false
            property_markers.forEach(marker => {
                let point = new T.LngLat(marker.longitude, marker.latitude);
                // 创建标记
                const markerIcon = new T.Icon({
                    iconUrl: 'https://api.tianditu.gov.cn/img/map/marker.png',
                    iconSize: new T.Point(25, 25),
                    iconAnchor: new T.Point(12, 25)
                });
                const currentMarker = new T.Marker(point, {icon: markerIcon});
                map.addOverLay(currentMarker);
                if (!setCenter){
                    map.centerAndZoom(point, 18); // 定位到第一个点位
                    setCenter = true
                }
                // 添加点击事件，点击时打开信息窗口
                currentMarker.addEventListener('click', () => {
                    const infoWindow = new T.InfoWindow(marker.name);
                    currentMarker.openInfoWindow(infoWindow);
                });
            });
        })
        .catch(error => {
            console.error('获取点位信息失败:', error);
        });
}

// 页面加载完成后初始化地图
fetch('/estate/tianditu_map/get_ak')
    .then(response => response.json())
    .then(data => {
        const tiandituMapAK = data.ak; // 获取天地图地图AK
        if (!tiandituMapAK) {
            console.error('天地图地图AK未配置');
            return;
        }

        // 加载天地图地图API
        loadPropertiesTiandituMapScript(tiandituMapAK, 'initPropertiesTiandituMap');
        console.info('页面加载完成后初始化地图完成');
    })
    .catch(error => {
        console.error('获取天地图地图AK失败:', error);
    });
