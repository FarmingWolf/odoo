// // 动态加载百度地图API
// function loadPropertiesBaiduMapScript(apiKey, callback) {
//     console.log("enter loadPropertiesBaiduMapScript")
//     // 获取地图容器
//     const mapContainer = document.getElementById('properties_baidu_map_container');
//     if (!mapContainer) {
//         console.info('properties_baidu_map_container无地图容器页面不加载API');
//         return;
//     }
//     const script = document.createElement('script');
//     script.src = `https://api.map.baidu.com/api?v=3.0&ak=${apiKey}&callback=${callback}`;
//     script.async = true; // 异步加载
//     document.head.appendChild(script);
// }
//
// // 初始化地图
// async function initPropertiesBaiduMap() {
//     console.log("enter initPropertiesBaiduMap");
//     if (typeof BMap === 'undefined') {
//         console.info('百度地图API未成功加载');
//         return;
//     }
//
//     const map = new BMap.Map("properties_baidu_map_container");
//     if (typeof map === 'undefined') {
//         console.log('properties_baidu_map_container没找到……');
//         return;
//     }
//     // 创建矢量图标
//     const symbol_smile = new BMap.Symbol(BMap_Symbol_SHAPE_SMILE, {
//         scale: 5, // 图标大小
//         strokeColor: "red", // 边框颜色
//         fillColor: "blue" // 填充颜色
//     });
//     // 自定义图标
//     const icon_smile = new BMap.Icon(symbol_smile, new BMap.Size(23, 25), {
//         offset: new BMap.Size(10, 25), // 图标偏移量
//         imageOffset: new BMap.Size(0, 0) // 图片偏移量，用于调整图标颜色
//     });
//
//     // 获取地图容器
//     const mapContainer = document.getElementById('properties_baidu_map_container');
//     if (!mapContainer) {
//         console.info('properties_baidu_map_container地图容器未找到');
//         return;
//     }
//
//     fetch(`/estate/baidu_map/get_company_loc`, {
//         method: 'GET',
//         headers: {
//             'Accept': 'application/json',
//         },
//     })
//         .then(response => response.json())
//         .then(company_marker => {
//             company_marker.forEach(marker => {
//                 const point = new BMap.Point(marker.longitude, marker.latitude);
//                 console.log("longitude", marker.longitude, "latitude", marker.latitude)
//                 map.centerAndZoom(point, 18); // 初始化地图，设置中心点坐标和地图级别
//                 map.enableScrollWheelZoom(true); // 启用滚轮缩放
//             });
//         })
//             .catch(error => {
//                 console.error('获取点位信息失败:', error);
//             });
//
//     // 从Controller获取点位信息
//     await fetch(`/estate/baidu_map/get_all_properties`, {
//         method: 'GET',
//         headers: {
//             'Accept': 'application/json',
//         },
//     })
//         .then(response => response.json())
//         .then(property_markers => {
//             console.log("property_markers", property_markers);
//             property_markers.forEach(marker => {
//                 const point = new BMap.Point(marker.longitude, marker.latitude);
//                 const currentMarker = new BMap.Marker(point);
//                 map.addOverlay(currentMarker);
//                 // 添加点击事件，点击时打开信息窗口
//                 currentMarker.addEventListener('click', () => {
//                     const infoWindow = new BMap.InfoWindow(marker.name);
//                     currentMarker.openInfoWindow(infoWindow);
//                 });
//             });
//         })
//         .catch(error => {
//             console.error('获取点位信息失败:', error);
//         });
// }
//
// // 页面加载完成后初始化地图
// fetch('/estate_slides/baidu_map/get_ak')
//     .then(response => response.json())
//     .then(data => {
//         const baiduMapAK = data.ak; // 获取百度地图AK
//         if (!baiduMapAK) {
//             console.error('百度地图AK未配置');
//             return;
//         }
//
//         // 加载百度地图API
//         loadPropertiesBaiduMapScript(baiduMapAK, 'initPropertiesBaiduMap');
//         console.info('页面加载完成后初始化地图完成');
//     })
//     .catch(error => {
//         console.error('获取百度地图AK失败:', error);
//     });
