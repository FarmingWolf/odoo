// 动态加载百度地图API
function loadBaiduMapScript(apiKey, callback) {
    console.log("enter loadBaiduMapScript")
    // 获取地图容器
    const mapContainer = document.getElementById('baidu-map-container');
    if (!mapContainer) {
        console.info('baidu-map-container无地图容器网页不加载地图API');
        return;
    }

    const script = document.createElement('script');
    script.src = `https://api.map.baidu.com/api?v=3.0&ak=${apiKey}&callback=${callback}`;
    script.async = true; // 异步加载
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
async function initBaiduMap() {
    console.log("enter initBaiduMap");
    if (typeof BMap === 'undefined') {
        console.log('百度地图API未成功加载');
        return;
    }
    // 获取地图容器
    const mapContainer = document.getElementById('baidu-map-container');
    if (!mapContainer) {
        console.info('baidu-map-container地图容器未找到');
        return;
    }
    // 创建矢量图标
    const symbol_smile = new BMap.Symbol(BMap_Symbol_SHAPE_SMILE, {
        scale: 5, // 图标大小
        strokeColor: "red", // 边框颜色
        fillColor: "blue" // 填充颜色
    });
    // 自定义图标
    const icon_smile = new BMap.Icon(symbol_smile, new BMap.Size(23, 25), {
        offset: new BMap.Size(10, 25), // 图标偏移量
        imageOffset: new BMap.Size(0, 0) // 图片偏移量，用于调整图标颜色
    });

    // 获取记录ID、纬度和经度

    const hashParams = getHashParams();
    const property_id = hashParams.id;
    console.log('Current record ID:', property_id);
    const latitude = parseFloat(mapContainer.dataset.propertyLatitude) || 39.90469; // 默认纬度
    const longitude = parseFloat(mapContainer.dataset.propertyLongitude) || 116.40717; // 默认经度

    // 初始化地图
    const map = new BMap.Map("baidu-map-container");
    const point = new BMap.Point(longitude, latitude);
    const zoom = 18
    map.centerAndZoom(point, zoom); // 初始化地图，设置中心点坐标和地图级别
    map.enableScrollWheelZoom(true); // 启用滚轮缩放

    // 存储当前标记
    let currentMarker = null;
    let infoWindow = null;
    const infoMsg = "尚未明确标注地图点位！请点击地图标注点位"
    // 从Controller获取点位信息
    await fetch(`/estate/baidu_map/get_markers?property_id=${property_id}`, {
        method: 'GET',
        headers: {
            'Accept': 'application/json',
        },
    })
        .then(response => response.json())
        .then(property_markers => {
            console.log("property_markers", property_markers);
            property_markers.forEach(marker => {
                const point = new BMap.Point(marker.longitude, marker.latitude);

                currentMarker = new BMap.Marker(point);
                map.addOverlay(currentMarker);
                map.centerAndZoom(point, zoom); // 初始化地图，设置中心点坐标和地图级别
                // 添加信息窗口（可选）
                let infoName = marker.name
                if (marker.default_company_loc === "1") {
                    infoName = `<div> ${marker.name}<br>${infoMsg}</div>`
                }
                infoWindow = new BMap.InfoWindow(infoName);
                currentMarker.openInfoWindow(infoWindow);
            });
        })
        .catch(error => {
            console.error('获取点位信息失败:', error);
        });

    // 监听地图点击事件
    map.addEventListener('click', function (e) {
        const latitude = e.point.lat; // 纬度
        const longitude = e.point.lng; // 经度

        // 删除之前的标记
        if (currentMarker) {
            map.removeOverlay(currentMarker);
        }

        // 在地图上显示点击点的标记
        currentMarker = new BMap.Marker(e.point);
        map.addOverlay(currentMarker);
        // const infoWindow = new BMap.InfoWindow(currentMarker.name || "");
        if (typeof infoWindow === 'undefined') {
        } else {
            const newInfo = infoWindow.getContent().replace(infoMsg, "")
            infoWindow.setContent(newInfo)
        }
        currentMarker.openInfoWindow(infoWindow);

        // 如果是第一次点击，注册模块
        if (!window.updatePropertyLocation) {
            // 调用Odoo控制器的方法
            odoo.define('estate.baidu_map', ['@web/core/network/rpc_service'], function (require) {
                "use strict";

                const {jsonrpc} = require('@web/core/network/rpc_service');

                function updatePropertyLocation(property_id, latitude, longitude) {
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
                window.updatePropertyLocation = updatePropertyLocation;

                // 注册后调用已注册的方法
                window.updatePropertyLocation(property_id, e.point.lat, e.point.lng)
                    .then(function (result) {
                        console.log('click 1 Location updated successfully:', result);
                    })
                    .catch(function (error) {
                        console.error('click 1 Failed to update location:', error);
                    });
            });
        } else {

            // 直接调用已注册的方法
            window.updatePropertyLocation(property_id, e.point.lat, e.point.lng)
                .then(function (result) {
                    console.log('not click 1 Location updated successfully:', result);
                })
                .catch(function (error) {
                    console.error('not click 1 Failed to update location:', error);
                });
        }
    });

}

// 页面加载完成后初始化地图
console.log("baidu_map.js loaded");
fetch('/estate_slides/baidu_map/get_ak')
    .then(response => response.json())
    .then(data => {
        const baiduMapAK = data.ak; // 获取百度地图AK
        if (!baiduMapAK) {
            console.error('百度地图AK未配置');
            return;
        }

        // 加载百度地图API
        loadBaiduMapScript(baiduMapAK, 'initBaiduMap');
        console.info('页面加载完成后初始化地图完成');
    })
    .catch(error => {
        console.error('获取百度地图AK失败:', error);
    });
