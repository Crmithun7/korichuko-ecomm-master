(function(){
  const sidebar = document.getElementById("sidebar");
  const toggle  = document.getElementById("sidebarToggle");
  if (toggle && sidebar) {
    toggle.addEventListener("click", () => sidebar.classList.toggle("open"));
    // Close when clicking outside on mobile
    document.addEventListener("click", (e) => {
      if (window.innerWidth >= 992) return;
      if (!sidebar.contains(e.target) && !toggle.contains(e.target)) {
        sidebar.classList.remove("open");
      }
    });
  }
})();
