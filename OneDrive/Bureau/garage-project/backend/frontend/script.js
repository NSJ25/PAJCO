const API = "http:// 10.251.21.201:5000"; // ton backend Flask
const PICO_ENTREE = "http://10.251.21.113:8081/ouvrir";
const PICO_SORTIE = "http://10.251.21.113:8081/sortie";

// Boutons
document.getElementById("btn-entree").onclick = function () {
  envoyer("entree");
};
document.getElementById("btn-sortie").onclick = function () {
  envoyer("sortie");
};

function envoyer(action) {
  let badge = document.getElementById("badge").value.trim();
  if (!badge) {
    alert("Entrez un ID badge !");
    return;
  }

  // Vérification sur le backend
  fetch(API + "/check", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ badge: badge }),
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.access) {
        alert("Bienvenue " + data.prenom + " " + data.nom);

        // Ouvrir la barrière correspondante
        let url =
          action === "entree"
            ? PICO_ENTREE + "?badge=" + badge
            : PICO_SORTIE + "?badge=" + badge;
        fetch(url)
          .then((r) => console.log(action + " ok"))
          .catch((e) => console.log("Erreur Pico", e));
      } else {
        alert("Accès refusé");
      }
    })
    .catch((e) => console.log("Erreur backend", e));
}

// Actualisation du nombre de places toutes les 1s
function refresh() {
  fetch(API + "/places")
    .then((r) => r.json())
    .then((data) => {
      document.getElementById("places").innerText =
        "Places restantes : " + data.places;
    })
    .catch((e) => console.log("Erreur refresh", e));
}

setInterval(refresh, 1000);
