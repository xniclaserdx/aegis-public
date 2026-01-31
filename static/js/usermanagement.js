// User Management JavaScript
function getSelectedUsers() {
    const checkboxes = document.querySelectorAll('.user-checkbox:checked');
    return Array.from(checkboxes).map(checkbox => checkbox.value).join(';');
}

function removeUsers() {
    const selectedUsers = getSelectedUsers();
    location.href = `/remove_users/${selectedUsers}`;
}

function changeRole() {
    const selectedUsers = getSelectedUsers();
    location.href = `/change_rank/${selectedUsers}`;
}

// Dark Mode Toggle
if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    document.body.classList.add('dark');
}
document.getElementById('toggleDarkMode').addEventListener('click', () => {
    document.body.classList.toggle('dark');
});
