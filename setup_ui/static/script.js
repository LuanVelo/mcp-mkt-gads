/* Google Ads MCP — Setup UI */

document.addEventListener('DOMContentLoaded', () => {
  formatCustomerIdInputs();
});

/**
 * Aplica máscara xxx-xxx-xxxx nos campos de Customer ID enquanto o usuário digita.
 */
function formatCustomerIdInputs() {
  const ids = ['customer_id', 'login_customer_id'];
  ids.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('input', () => {
      let val = el.value.replace(/\D/g, '').slice(0, 10);
      if (val.length > 6) {
        val = val.slice(0, 3) + '-' + val.slice(3, 6) + '-' + val.slice(6);
      } else if (val.length > 3) {
        val = val.slice(0, 3) + '-' + val.slice(3);
      }
      el.value = val;
    });
  });
}
