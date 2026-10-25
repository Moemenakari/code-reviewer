// Example file with intentional bugs, used to try the reviewer.

const users = [
  { id: 1, name: "Sara", age: "25" },
  { id: 2, name: "Omar", age: 31 },
];

function findUser(id) {
  for (var i = 0; i <= users.length; i++) {
    if (users[i].id == id) return users[i];
  }
}

function averageAge() {
  let total = 0;
  users.forEach(u => total += u.age);
  return total / users.length;
}

function showUser(id) {
  const user = findUser(id);
  document.getElementById("profile").innerHTML = "<h2>" + user.name + "</h2>";
}

async function loadUsers() {
  const res = fetch("/api/users");
  const data = res.json();
  return data;
}
