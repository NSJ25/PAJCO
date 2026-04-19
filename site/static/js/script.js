// fonction d'initialisation
function init() {
    console.log("Bivenuevenue sur PAJCO !");
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


// fonction pour afficher le popup avec le formulaire d'entrée du parking
function enter() {
    afficherPopup("dialog");
    const msg = getId("dialogMessage");
    msg.innerHTML = `
    <h2 class="title2"> Bienvenue dans le parking ! </h2>
    <P class="text"> Mettez vos informations de connexion pour entrer dans parking.</p>
    
    <form id="openDoorForm" onsubmit="return false;">
        <fieldset>
            <legend>Entrée dans le parking</legend>

            <label for="username">Nom d'utilisateur:</label>
            <input type="text" id="username" name="username" required />
            <br />
            <label for="password">Mot de passe:</label>
            <input type="password" id="password" name="password" required />
            <br />
            <button type="button" onclick="OpenDoor()"> Ouvrir la porte d'entrée du parking </button>
        </fieldset>
    </form> `;
}

// fonction pour ouvrir la porte d'entrée du parking
function OpenDoor() {
    // Récupérer les valeurs des champs de formulaire
    let username = getId("username").value;
    let password = getId("password").value;

    // Envoyer la requête POST
    let xhr = new XMLHttpRequest();
    xhr.open("POST", "/openDoor", true);

    // Ajouter les en-têtes de la requête
    xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
    
    // Envoyer les données de la requête
    xhr.send(
        "username=" + encodeURIComponent(username) +
        "&password=" + encodeURIComponent(password)
    );

    // Gérer la réponse du serveur
    xhr.onload = function() {
        if (xhr.status === 200) {
            let response = JSON.parse(xhr.responseText);
            let msg = getId("dialogMessage");
            if (response.status === "access authorisé") {
                msg.innerHTML = `Bienvenue a la maison : ${response.prenom} ${response.nom} !`;
            } else {
                msg.innerHTML = "Nom d'utilisateur ou mot de passe incorrect.";
            }
            afficherPopup("dialog");
        } else {
            console.error("Erreur serveur : " + xhr.status);
        }
    }
}

// fonction pour afficher le popup avec le formulaire de sortie du parking
function exit() {
    afficherPopup("dialog");
    const msg = getId("dialogMessage");
    msg.innerHTML = `
    <h2 class="title2"> A revoir et a bientôt ! </h2>
    <P class="text"> Mettez vos informations de connexion pour sortir du parking.</p>
    <form id="closeDoorForm" onsubmit="return false;">
        <fieldset>
            <legend>Sortie du parking</legend>

            <label for="username">Nom d'utilisateur:</label>
            <input type="text" id="username" name="username" required />
            <br />
            <label for="password">Mot de passe:</label>
            <input type="password" id="password" name="password" required />
            <br />
            <button type="button" onclick="CloseDoor()"> Ouvrir la porte de sortie du parking </button>
        </fieldset>
    </form> `;
}

// fonction pour ouvrir la porte de sortie du parking
function CloseDoor(){
    // Récupérer les valeurs des champs de formulaire
    let username = getId("username").value;
    let password = getId("password").value;

    // Envoyer la requête POST
    let xhr = new XMLHttpRequest();
    xhr.open("POST", "/closeDoor", true);
    xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
    xhr.send(
        "username=" + encodeURIComponent(username) +
        "&password=" + encodeURIComponent(password)
    );
    xhr.onload = function() {
        let response = JSON.parse(xhr.responseText);
        let msg = getId("dialogMessage");
        if (response.status === "access authorisé") {
            msg.innerHTML = `Au revoir et a bientôt ! ${response.prenom} ${response.nom} !`;
        } else {
            msg.innerHTML = "Nom d'utilisateur ou mot de passe incorrect.";
        }
        afficherPopup("dialog");
    }       




}


























