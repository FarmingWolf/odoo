// 动态加载天地图API
function loadTiandituMapScript(apiKey, callback) {
    console.log("enter loadTiandituMapScript");
    // 获取地图容器
    const mapContainer = document.getElementById('property-map-container');
    if (!mapContainer) {
        console.info('property-map-container无地图容器网页不加载地图API');
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

function getHashParams() {
    const hash = window.location.hash.substr(1); // 去掉 # 号
    const params = {};

    hash.split('&').forEach(param => {
        const [key, value] = param.split('=');
        if (key && value) {
            params[key] = decodeURIComponent(value);
        }
    });

    return params;
}

// 初始化地图
async function initEstateTiandituMap() {
    console.log("enter initEstateTiandituMap");

    // 检查天地图API是否加载成功
    if (typeof T === 'undefined') {
        console.log('天地图API未成功加载');
        return;
    }

    // 获取地图容器
    const mapContainer = document.getElementById('property-map-container');
    if (!mapContainer) {
        console.info('property-map-container地图容器未找到');
        return;
    }

    // 获取记录ID、纬度和经度
    const hashParams = getHashParams();
    const property_id = hashParams.id;
    console.log('Current record ID:', property_id);

    // 从数据集获取经纬度，如果没有则使用默认值
    const latitude = parseFloat(mapContainer.dataset.propertyLatitude) || 39.90469;
    const longitude = parseFloat(mapContainer.dataset.propertyLongitude) || 116.40717;

    // 初始化地图
    let map = new T.Map('property-map-container', {
                projection: 'EPSG:4326'
            });
    const point = new T.LngLat(longitude, latitude);
    const zoom = 18;

    // 设置地图中心点和缩放级别
    map.centerAndZoom(point, zoom);
    // 启用滚轮缩放
    map.enableScrollWheelZoom();

    // 添加控件
    const control = new T.Control.Zoom();
    control.setPosition("topright");
    map.addControl(control);

    // 存储当前标记
    let currentMarker = null;
    let infoWindow = null;
    const infoMsg = "尚未明确标注地图点位！请点击地图标注点位";

    // 从服务器获取点位信息
    try {
        const response = await fetch(`/estate/tianditu_map/get_markers?property_id=${property_id}`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
            },
        });

        const property_markers = await response.json();
        console.log("property_markers", property_markers);

        property_markers.forEach(marker => {
            const point = new T.LngLat(marker.longitude, marker.latitude);

            // 创建标记
            const markerIcon = new T.Icon({
                iconUrl: 'https://api.tianditu.gov.cn/img/map/marker.png',
                iconSize: new T.Point(25, 25),
                iconAnchor: new T.Point(12, 25)
            });

            currentMarker = new T.Marker(point, {icon: markerIcon});
            map.addOverLay(currentMarker);
            map.centerAndZoom(point, zoom);

            // 添加信息窗口
            let infoName = marker.name;
            if (marker.default_company_loc === "1") {
                infoName = `<div>${marker.name}<br>${infoMsg}</div>`;
            }

            infoWindow = new T.InfoWindow(infoName);
            currentMarker.openInfoWindow(infoWindow);
        });
    } catch (error) {
        console.error('获取点位信息失败:', error);
    }

    // 监听地图点击事件
    map.addEventListener('click', function (e) {
        const latitude = e.lnglat.getLat();
        const longitude = e.lnglat.getLng();

        // 删除之前的标记
        if (currentMarker) {
            map.removeOverLay(currentMarker);
        }

        // 创建新标记
        const markerIcon = new T.Icon({
            iconUrl: 'https://api.tianditu.gov.cn/img/map/marker.png',
            iconSize: new T.Point(25, 25),
            iconAnchor: new T.Point(12, 25)
        });

        currentMarker = new T.Marker(e.lnglat, {icon: markerIcon});
        map.addOverLay(currentMarker);

        // 更新信息窗口内容
        if (infoWindow) {
            const newInfo = infoWindow.getContent().replace(infoMsg, "");
            infoWindow.setContent(newInfo);
        }
        currentMarker.openInfoWindow(infoWindow);

        // 如果是第一次点击，注册模块
        if (!window.updatePropertyTTTLocation) {
            // 调用Odoo控制器的方法
            odoo.define('estate.tianditu_map', ['@web/core/network/rpc_service'], function (require) {
                "use strict";

                const {jsonrpc} = require('@web/core/network/rpc_service');

                function updatePropertyTTTLocation(property_id, latitude, longitude) {
                    // 发送 RPC 请求
                    return jsonrpc('/estate/update_property_location', {
                        property_id: parseInt(property_id),
                        latitude: latitude,
                        longitude: longitude,
                    }).then(function (result) {
                        console.log('Location updated successfully:', result);
                    }).catch(function (error) {
                        console.error('Failed to update location:', error);
                    });
                }
                // 将方法暴露给模块
                window.updatePropertyTTTLocation = updatePropertyTTTLocation;

                // 注册后调用已注册的方法
                window.updatePropertyTTTLocation(property_id, latitude, longitude)
                    .then(function (result) {
                        console.log('click 1 Location updated successfully:', result);
                    })
                    .catch(function (error) {
                        console.error('click 1 Failed to update location:', error);
                    });
            });
        } else {

            // 直接调用已注册的方法
            window.updatePropertyTTTLocation(property_id, latitude, longitude)
                .then(function (result) {
                    console.log('not click 1 Location updated successfully:', result);
                })
                .catch(function (error) {
                    console.error('not click 1 Failed to update location:', error);
                });
        }
    });

    console.log("initEstateTiandituMap over");
}

// 页面加载完成后初始化地图
console.log("tianditu_map.js loaded");
fetch('/estate/tianditu_map/get_ak')
    .then(response => response.json())
    .then(data => {
        const tiandituMapAK = data.ak; // 获取天地图地图AK
        if (!tiandituMapAK) {
            console.error('天地图AK未配置');
            return;
        }

        // 加载天地图地图API
        loadTiandituMapScript(tiandituMapAK, "initEstateTiandituMap");
        console.info('页面加载完成后初始化天地图完成');
    })
    .catch(error => {
        console.error('获取天地图AK失败:', error);
    });
