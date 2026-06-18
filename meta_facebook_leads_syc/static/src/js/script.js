// Filter buttons functionality
const filterBtns = document.querySelectorAll(".filter-btn");
const sections = document.querySelectorAll(
  "#screenshot-section, #features-section, #questions-section, #release-section"
);

filterBtns.forEach((btn) => {
  btn.addEventListener("click", () => {
    // Remove active class from all buttons
    filterBtns.forEach((b) => b.classList.remove("active"));

    // Add active class to clicked button
    btn.classList.add("active");

    // Hide all sections
    sections.forEach((s) => (s.style.display = "none"));

    // Show target section
    const target = btn.dataset.target;
    const targetSection = document.getElementById(target);
    if (targetSection) {
      targetSection.style.display = "block";
      targetSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });
});

// Email button
document.querySelector(".btn-email")?.addEventListener("click", () => {
  window.open("mailto:support@ebitdasolutions.com");
});


// LinkedIn button
document.querySelector(".btn-linkedin")?.addEventListener("click", () => {
  window.open(
    "https://www.linkedin.com/company/ebitda-solutions/posts/?feedView=all",
    "_blank"
  );
});

// WhatsApp button
document.querySelector(".btn-whatsapp")?.addEventListener("click", () => {
  window.open("https://wa.me/923116427867", "_blank");
});

// Blog button
document.querySelector(".btn-blog")?.addEventListener("click", () => {
  window.open("https://www.ebitdasolutions.com/", "_blank");
});

// Video button
document.querySelector(".btn-video")?.addEventListener("click", () => {
  window.open("https://youtu.be/DNufeUxYdlQ?si=ltjpWKlRfkPnuGOn", "_blank");
});

function toggleScreenshotSection(event) {
    event.preventDefault(); // <-- Prevents page refresh
    var section = document.getElementById('screenshot_section');
    if (section.style.display === 'none' || section.style.display === '') {
        section.style.display = 'block';
        section.scrollIntoView({ behavior: 'smooth' });
    } else {
        section.style.display = 'none';
    }
}