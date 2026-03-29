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

// fonction pour ouvrir la porte
function OpenDoor() {
    let username = getId("username").value;
    let password = getId("password").value;

    let xhr = new XMLHttpRequest();
    xhr.open("POST", "/openDoor", true);
    xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
    xhr.send(
        "username=" + encodeURIComponent(username) +
        "&password=" + encodeURIComponent(password)
    );

    xhr.onload = function() {
        if (xhr.status === 200) {
            let response = JSON.parse(xhr.responseText);
            let msg = getId("dialogMessage");
            if (response.status === "ACCESS_GRANTED") {
                msg.innerHTML = "Barrière ouverte !";
            } else {
                msg.innerHTML = "Nom d'utilisateur ou mot de passe incorrect.";
            }
            afficherPopup("dialog");
        } else {
            console.error("Erreur serveur : " + xhr.status);
        }
    }
}
