/** @odoo-module **/

import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";

export class MapComponent extends Component {
  static template = "MapComponent";
  static props = {
    id: { type: String },
    markers: { type: Array },
    onMarkerClick: { type: Function },
  };

  setup() {
    this.map = null;
    this.markerLayer = null;

    onMounted(() => {
      this.initMap();
    });

    onWillUnmount(() => {
      this.destroyMap();
    });
  }

  async initMap() {
    // 加载天地图API
    await loadTDTMapAPI();

    // 初始化地图
    this.map = new T.Map(this.props.id);
    this.map.centerAndZoom(new T.LngLat(116.4074, 39.9042), 11);
    this.map.setMapType(TMAP_NORMAL_MAP);
    this.map.enableScrollWheelZoom(false); // 禁用缩放

    // 添加北京市行政区划图层
    this.addDistrictLayer();

    // 添加标记点
    this.addMarkers();
  }

  addDistrictLayer() {
    // 添加北京市行政区划图层
    const districtLayer = new T.DistrictLayer({
      showLabel: true,
      style: {
        fillColor: "rgba(0, 63, 127, 0.3)",
        color: "#0074D9",
        weight: 2,
      }
    });
    districtLayer.setZIndex(1);
    districtLayer.search("北京市");
    this.map.addLayer(districtLayer);
  }

  addMarkers() {
    this.markerLayer = new T.FeatureGroup();

    this.props.markers.forEach(markerData => {
      const marker = new T.Marker(new T.LngLat(markerData.lng, markerData.lat), {
        icon: new T.Icon({
          iconUrl: "/web/static/img/marker-icon.png",
          iconSize: [25, 41],
          iconAnchor: [12, 41],
          popupAnchor: [1, -34],
        }),
        title: markerData.name,
      });

      // 信息窗口
      const infoWindow = new T.InfoWindow(`
        <div style="color:#333;padding:10px;">
          <h4 style="margin:0 0 5px 0;">${markerData.name}</h4>
          <p>${markerData.info}</p>
        </div>
      `);

      marker.bindPopup(infoWindow).openPopup();

      // 点击事件
      marker.on("click", () => {
        this.props.onMarkerClick(markerData);
      });

      this.markerLayer.addLayer(marker);
    });

    this.map.addLayer(this.markerLayer);
  }

  destroyMap() {
    if (this.map) {
      this.map.remove();
      this.map = null;
    }
  }
}
