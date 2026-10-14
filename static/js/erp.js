// SME-ERP client helpers: dynamic line formsets, auto-dismiss alerts.
(function () {
  "use strict";

  // Add a row to a Django formset: <button data-formset-add="prefix">. The empty form lives in
  // <template id="prefix-empty">, rows go into <tbody id="prefix-rows">.
  document.addEventListener("click", function (event) {
    const button = event.target.closest("[data-formset-add]");
    if (!button) return;
    event.preventDefault();
    const prefix = button.dataset.formsetAdd;
    const total = document.getElementById("id_" + prefix + "-TOTAL_FORMS");
    const template = document.getElementById(prefix + "-empty");
    const rows = document.getElementById(prefix + "-rows");
    const index = parseInt(total.value, 10);
    rows.insertAdjacentHTML("beforeend", template.innerHTML.replace(/__prefix__/g, index));
    total.value = index + 1;
  });

  // Hide alerts after a few seconds.
  window.setTimeout(function () {
    document.querySelectorAll(".alert-dismissible.auto-hide").forEach(function (el) {
      if (window.bootstrap) bootstrap.Alert.getOrCreateInstance(el).close();
    });
  }, 6000);
})();
