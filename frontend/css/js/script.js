document.getElementById("appointmentForm").addEventListener("submit", function(e) {
    let date = new Date(document.getElementById("date").value);
    
    if (date.getDay() === 0) { // Sunday
        alert("Appointments are not available on Sunday!");
        e.preventDefault();
    }
});
