// Kéo thả khối trang Tổng quan (migration 034, theo Dashboard.dc.html).
//
// File JavaScript DUY NHẤT của app, không thư viện ngoài. Máy chủ đã vẽ sẵn
// đúng bố cục (thứ tự + grid-column/grid-row), nên file này KHÔNG dựng gì lúc
// tải trang — nó chỉ nghe thao tác, đổi DOM tại chỗ, rồi gửi bố cục về
// POST /tong-quan/bo-cuc. Máy chủ lọc lại mọi thứ (kome/web/bo_cuc.py), nên
// ở đây không cần kiểm hợp lệ gì ngoài kẹp kích thước cho hình vẽ tức thời.
//
// Ba đường thao tác, cùng đi tới một hàm `luu()`:
//   * chuột: kéo nút ⠿ để đổi chỗ, kéo góc phải dưới để đổi kích thước;
//   * bàn phím: nút ⠿ đang chọn + ←/→ đổi chỗ, Shift + ←/→ đổi rộng,
//     Shift + ↑/↓ đổi cao;
//   * nút ✕ ẩn khối, ô "Thêm chức năng vào dashboard" hiện lại.
(function () {
  "use strict";
  var luoi = document.querySelector(".luoi-tq[data-luu]");
  if (!luoi) return;
  var RONG_TOI_DA = 3, CAO_TOI_DA = 4;   // khớp kome/web/bo_cuc.py
  var bao = document.getElementById("bao-bo-cuc");

  function khoi() { return Array.prototype.slice.call(luoi.querySelectorAll(":scope > .khoi-tq")); }
  function nhan(k) { var h = k.querySelector("h2"); return h ? h.textContent.trim() : k.dataset.khoi; }
  function noi(chu) { if (bao) bao.textContent = chu; }

  function datCo(k, rong, cao) {
    rong = Math.max(1, Math.min(RONG_TOI_DA, rong));
    cao = Math.max(1, Math.min(CAO_TOI_DA, cao));
    k.dataset.rong = rong; k.dataset.cao = cao;
    k.style.gridColumn = "span " + rong;
    k.style.gridRow = "span " + cao;
  }

  var hen = null;
  function luu() {
    // Gom các thay đổi dồn dập (kéo góc liên tục) thành một lần gửi.
    clearTimeout(hen);
    hen = setTimeout(function () {
      var bo_cuc = khoi().map(function (k) {
        return {id: k.dataset.khoi, rong: +k.dataset.rong, cao: +k.dataset.cao, an: k.hidden};
      });
      fetch(luoi.dataset.luu, {
        method: "POST", credentials: "same-origin",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(bo_cuc)
      }).then(function (r) {
        if (!r.ok) noi("Không lưu được bố cục — tải lại trang để thấy bố cục đang lưu.");
      }).catch(function () {
        noi("Không lưu được bố cục — mất kết nối tới máy chủ.");
      });
    }, 300);
  }

  function capNhatDanhSachAn() {
    var soAn = 0;
    khoi().forEach(function (k) {
      var muc = document.querySelector('[data-muc-an="' + k.dataset.khoi + '"]');
      if (muc) muc.hidden = !k.hidden;
      if (k.hidden) soAn++;
    });
    var dem = document.querySelector("[data-dem-an]");
    if (dem) dem.textContent = soAn;
    var het = document.querySelector("[data-het-an]");
    if (het) het.hidden = soAn > 0;
  }

  // ---- Ẩn / hiện ------------------------------------------------------
  luoi.addEventListener("click", function (e) {
    var nut = e.target.closest(".an-khoi");
    if (!nut) return;
    var k = nut.closest(".khoi-tq");
    k.hidden = true;
    capNhatDanhSachAn(); luu();
    noi("Đã ẩn khối " + nhan(k) + ". Hiện lại ở mục Thêm chức năng vào dashboard.");
  });
  document.addEventListener("click", function (e) {
    var nut = e.target.closest("[data-hien]");
    if (!nut) return;
    var k = luoi.querySelector('[data-khoi="' + nut.dataset.hien + '"]');
    if (!k) return;
    k.hidden = false;
    capNhatDanhSachAn(); luu();
    noi("Đã hiện khối " + nhan(k) + ".");
    var keo = k.querySelector(".keo-khoi");
    if (keo) keo.focus();
  });

  // ---- Kéo đổi chỗ (chuột) --------------------------------------------
  // Khối chỉ `draggable` trong lúc đang giữ nút ⠿: để khối luôn draggable là
  // bôi đen chữ hay kéo một liên kết trong khối cũng thành kéo cả khối.
  var dangKeo = null;
  function boDich() {
    khoi().forEach(function (k) { k.classList.remove("dich-truoc", "dich-sau"); });
  }
  luoi.addEventListener("pointerdown", function (e) {
    var nut = e.target.closest(".keo-khoi");
    if (nut) nut.closest(".khoi-tq").draggable = true;
  });
  luoi.addEventListener("dragstart", function (e) {
    var k = e.target.closest && e.target.closest(".khoi-tq");
    if (!k || !k.draggable) return;
    dangKeo = k;
    k.classList.add("dang-keo");
    e.dataTransfer.effectAllowed = "move";
    try { e.dataTransfer.setData("text/plain", k.dataset.khoi); } catch (_) {}
  });
  function truocHaySau(dich, e) {
    var r = dich.getBoundingClientRect();
    return e.clientX < r.left + r.width / 2 ? "truoc" : "sau";
  }
  luoi.addEventListener("dragover", function (e) {
    if (!dangKeo) return;
    var dich = e.target.closest(".khoi-tq");
    if (!dich || dich === dangKeo) return;
    e.preventDefault();
    boDich();
    dich.classList.add(truocHaySau(dich, e) === "truoc" ? "dich-truoc" : "dich-sau");
  });
  luoi.addEventListener("drop", function (e) {
    if (!dangKeo) return;
    var dich = e.target.closest(".khoi-tq");
    e.preventDefault();
    if (dich && dich !== dangKeo) {
      luoi.insertBefore(dangKeo, truocHaySau(dich, e) === "truoc" ? dich : dich.nextSibling);
      luu();
      noi("Đã chuyển khối " + nhan(dangKeo) + ".");
    }
  });
  luoi.addEventListener("dragend", function () {
    if (dangKeo) { dangKeo.classList.remove("dang-keo"); dangKeo.draggable = false; }
    dangKeo = null; boDich();
  });
  // Bấm ⠿ mà không kéo: trả draggable về false.
  document.addEventListener("pointerup", function () {
    if (!dangKeo) khoi().forEach(function (k) { k.draggable = false; });
  });

  // ---- Kéo góc đổi kích thước (chuột / cảm ứng) -----------------------
  // Cùng phép tính của gói thiết kế: bề rộng một cột + khe, chiều cao một
  // hàng 150px + khe, làm tròn về số ô gần nhất.
  luoi.addEventListener("pointerdown", function (e) {
    var goc = e.target.closest(".co-gian");
    if (!goc) return;
    e.preventDefault();
    var k = goc.closest(".khoi-tq");
    var kieu = getComputedStyle(luoi);
    var khe = parseFloat(kieu.columnGap) || 12;
    var oRong = (luoi.clientWidth - (RONG_TOI_DA - 1) * khe) / RONG_TOI_DA + khe;
    var oCao = 150 + (parseFloat(kieu.rowGap) || 12);
    var x0 = e.clientX, y0 = e.clientY, w0 = k.offsetWidth, h0 = k.offsetHeight;
    goc.setPointerCapture(e.pointerId);
    function keo(ev) {
      datCo(k, Math.round((w0 + ev.clientX - x0) / oRong),
               Math.round((h0 + ev.clientY - y0) / oCao));
    }
    function nha() {
      goc.removeEventListener("pointermove", keo);
      goc.removeEventListener("pointerup", nha);
      goc.removeEventListener("pointercancel", nha);
      luu();
      noi("Khối " + nhan(k) + ": rộng " + k.dataset.rong + " cột, cao " + k.dataset.cao + " hàng.");
    }
    goc.addEventListener("pointermove", keo);
    goc.addEventListener("pointerup", nha);
    goc.addEventListener("pointercancel", nha);
  });

  // ---- Bàn phím trên nút ⠿ --------------------------------------------
  luoi.addEventListener("keydown", function (e) {
    var nut = e.target.closest(".keo-khoi");
    if (!nut) return;
    var k = nut.closest(".khoi-tq");
    var rong = +k.dataset.rong, cao = +k.dataset.cao;
    if (e.shiftKey) {
      if (e.key === "ArrowLeft") rong--;
      else if (e.key === "ArrowRight") rong++;
      else if (e.key === "ArrowUp") cao--;
      else if (e.key === "ArrowDown") cao++;
      else return;
      e.preventDefault();
      datCo(k, rong, cao); luu();
      noi("Khối " + nhan(k) + ": rộng " + k.dataset.rong + " cột, cao " + k.dataset.cao + " hàng.");
      return;
    }
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight" &&
        e.key !== "ArrowUp" && e.key !== "ArrowDown") return;
    e.preventDefault();
    // Đổi chỗ với khối ĐANG HIỆN liền trước/sau — khối ẩn không chiếm chỗ.
    var hien = khoi().filter(function (x) { return !x.hidden; });
    var i = hien.indexOf(k);
    var lui = e.key === "ArrowLeft" || e.key === "ArrowUp";
    var j = lui ? i - 1 : i + 1;
    if (j < 0 || j >= hien.length) return;
    luoi.insertBefore(k, lui ? hien[j] : hien[j].nextSibling);
    nut.focus();
    luu();
    noi("Khối " + nhan(k) + " ở vị trí " + (j + 1) + " trên " + hien.length + ".");
  });
})();
