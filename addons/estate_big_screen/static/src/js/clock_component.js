/** @odoo-module **/

import { Component, onMounted, onWillUnmount, useState, xml } from "@odoo/owl";

export class ClockComponent extends Component {
  static template = xml`
    <div class="dashboard-clock">
      <div class="clock-date" t-esc="state.date" />
      <div class="clock-week" t-esc="state.week" />
      <div class="clock-time" t-esc="state.time" />
    </div>
  `;

  setup() {
    this.state = useState({
      date: "",
      time: "",
      week: "",
    });

    this.timer = null;

    onMounted(() => {
      this.updateClock();
      this.timer = setInterval(this.updateClock.bind(this), 1000);
    });

    onWillUnmount(() => {
      if (this.timer) {
        clearInterval(this.timer);
      }
    });
  }

  updateClock() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    const hours = String(now.getHours()).padStart(2, "0");
    const minutes = String(now.getMinutes()).padStart(2, "0");
    const seconds = String(now.getSeconds()).padStart(2, "0");
    const weekDays = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"];
    const week = weekDays[now.getDay()];

    this.state.date = `${year}年${month}月${day}日`;
    this.state.time = `${hours}:${minutes}:${seconds}`;
    this.state.week = week;
  }
}
