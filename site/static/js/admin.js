// fonction d'initialisation
function init() {
    console.log("Bivenuevenue sur PAJCO !");
    loadUsers(); // Charger les utilisateurs au démarrage
}

// fonction pour récupérer un élément par son ID
function getId(id) {
    return document.getElementById(id);
}

// fonction pour afficher un popup
function afficherPopup(id) {
    return document.getElementById(id).showModal();
}

// fonction pour fermer un popup
function fermerPopup(id) {
    return document.getElementById(id).close();
}

// fonction pour charger les utilisateurs
function loadUsers() {
    let xhr = new XMLHttpRequest();
    xhr.open("GET", "/users", true);
    xhr.send();
    xhr.onload = function() {
        if (xhr.status === 200) {
            let response = JSON.parse(xhr.responseText);
            let listUsers = getId("listUsers");
            let tab = "";
            // Boucle pour chaque utilisateur
            for(let elem of response){
                tab += `<tr>`;
                tab += `<td>${elem.nom}</td>`;
                tab += `<td>${elem.prenom}</td>`;
                tab += `<td>${elem.username}</td>`;
                tab += `<td>${elem.etat}</td>`;
                tab += `</tr>`;
            }
            // Afficher le tableau dans la liste des utilisateurs
            listUsers.innerHTML = tab;
        } else {
            console.error("Erreur serveur : " + xhr.status);
        }
    }
}


function AddUser() {
    afficherPopup("dialog");

    const dialogTitle = getId("dialogTitle");
    dialogTitle.innerHTML = "Ajouter un utilisateur";

    const dialogContent = getId("dialogContent");

    // Injecter le formulaire dans le dialog
    dialogContent.innerHTML = `
        <label>Nom :</label>
        <input type="text" id="nom" required><br>

        <label>Prénom :</label>
        <input type="text" id="prenom" required><br>

        <label>Username :</label>
        <input type="text" id="username" required><br>

        <label>Password :</label>
        <input type="password" id="password" required><br>

        <button id="btnAddUser" type="button">Ajouter</button>
    `;

    // Sécuriser l'ajout de l'événement
    const btn = getId("btnAddUser");
    if (btn) {
        btn.addEventListener("click", function(e) {
            e.preventDefault(); // empêche tout refresh

            const nom = getId("nom").value.trim();
            const prenom = getId("prenom").value.trim();
            const username = getId("username").value.trim();
            const password = getId("password").value.trim();

            if (!nom || !prenom || !username || !password) {
                alert("Veuillez remplir tous les champs !");
                return;
            }

            const xhr = new XMLHttpRequest();
            xhr.open("POST", "/addUser", true);
            xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");

            xhr.onload = function() {
                if (xhr.status === 200) {
                    const response = JSON.parse(xhr.responseText);

                    // Afficher le message
                    dialogTitle.innerHTML = "Message";
                    dialogContent.innerHTML = `<p>${response.status}</p>`;

                    // Recharger le tableau
                    loadUsers();
                } else {
                    console.error("Erreur serveur : " + xhr.status);
                }
            };

            xhr.send(
                "nom=" + encodeURIComponent(nom) +
                "&prenom=" + encodeURIComponent(prenom) +
                "&username=" + encodeURIComponent(username) +
                "&password=" + encodeURIComponent(password)
            );
        });
    }
}



function removeUser() {
    afficherPopup("dialog");

    const dialogTitle = getId("dialogTitle");
    dialogTitle.innerHTML = "Supprimer un utilisateur";

    const dialogContent = getId("dialogContent");
    dialogContent.innerHTML = ` 
        <p>Attention : Supprimer un utilisateur supprimera toutes ses données.</p>
        <form id="removeUserForm">
            <label>Username :</label>
            <input type="text" id="username" required><br>
            <label>Password :</label>
            <input type="password" id="password" required><br>
            <button id="btnRemoveUser" type="button">Supprimer</button>
        </form>
        <p id="removeMessage" style="color: red; margin-top: 10px;"></p>
    `;

    let btn = getId("btnRemoveUser");
    if (btn) {
        btn.addEventListener("click", function(e) {
            e.preventDefault(); // empêche le refresh

            let username = getId("username").value.trim();
            let password = getId("password").value.trim();

            if (!username || !password) {
                getId("removeMessage").innerHTML = "Veuillez remplir tous les champs !";
                return;
            }

            let xhr = new XMLHttpRequest();
            xhr.open("POST", "/removeUser", true);
            xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
            xhr.onload = function() {
                if (xhr.status === 200) {
                    let response = JSON.parse(xhr.responseText);
                    getId("removeMessage").innerHTML = response.status;
                    // Fermer le popup
                    setTimeout(() => {
                        fermerPopup("dialog");
                    }, 2000);
                    // Recharger la liste des utilisateurs
                    loadUsers();
                } else {
                    getId("removeMessage").innerHTML = "Erreur serveur : " + xhr.status;
                }
            };
            xhr.send(
                "username=" + encodeURIComponent(username) +
                "&password=" + encodeURIComponent(password)
            );
        });
    }
}


