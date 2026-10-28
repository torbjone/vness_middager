/* Middager hos oss – ukemeny og middagsforslag. */

const DAGER = [
  { navn: "mandag", anledning: "hverdag" },
  { navn: "tirsdag", anledning: "hverdag" },
  { navn: "onsdag", anledning: "hverdag" },
  { navn: "torsdag", anledning: "hverdag" },
  { navn: "fredag", anledning: "helg" },
  { navn: "lørdag", anledning: "helg" },
  { navn: "søndag", anledning: "hverdag" },
];

const MIN_FISK = 3;

const SESONGNAVN = { vinter: "Vinter", var: "Vår", sommer: "Sommer", host: "Høst" };

const el = (id) => document.getElementById(id);

let retter = [];
let uke = [];
let tilfeldig = Math.random;

/* ---------- hjelpere ---------- */

function sesongNa(dato = new Date()) {
  const m = dato.getMonth() + 1;
  if (m === 12 || m <= 2) return "vinter";
  if (m <= 5) return "var";
  if (m <= 8) return "sommer";
  return "host";
}

function ukenummer(dato = new Date()) {
  const d = new Date(Date.UTC(dato.getFullYear(), dato.getMonth(), dato.getDate()));
  d.setUTCDate(d.getUTCDate() + 4 - (d.getUTCDay() || 7));
  const nyttar = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return Math.ceil(((d - nyttar) / 86400000 + 1) / 7);
}

/* Fast «tilfeldighet» per uke, slik at alle i familien ser samme ukemeny. */
function froRandom(fro) {
  let a = fro >>> 0;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function bland(liste, rnd) {
  const kopi = liste.slice();
  for (let i = kopi.length - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1));
    [kopi[i], kopi[j]] = [kopi[j], kopi[i]];
  }
  return kopi;
}

const erFisk = (rett) => rett.kategori === "fisk";

function passerDag(rett, dag) {
  return rett.anledning.includes(dag.anledning);
}

function iSesong(rett, sesong) {
  return rett.sesong.includes("hele-aret") || rett.sesong.includes(sesong);
}

/* Kandidater for en dag: helst retter i sesong, ellers alle som passer anledningen. */
function kandidater(dag, sesong, { kunFisk = false, utenFisk = false } = {}) {
  const grunn = retter.filter(
    (r) => passerDag(r, dag) && (!kunFisk || erFisk(r)) && (!utenFisk || !erFisk(r))
  );
  const iSesongen = grunn.filter((r) => iSesong(r, sesong));
  return iSesongen.length ? iSesongen : grunn;
}

/* ---------- ukemeny ---------- */

function lagUke(rnd, sesong) {
  for (let forsok = 0; forsok < 300; forsok++) {
    const plan = new Array(DAGER.length).fill(null);
    const brukt = new Set();

    // 1) Sikre minst tre fiskedager.
    const fiskedager = bland(
      DAGER.map((d, i) => i).filter((i) => kandidater(DAGER[i], sesong, { kunFisk: true }).length),
      rnd
    ).slice(0, MIN_FISK);

    let ok = fiskedager.length >= MIN_FISK;
    for (const i of fiskedager) {
      const valg = bland(kandidater(DAGER[i], sesong, { kunFisk: true }), rnd).find(
        (r) => !brukt.has(r.slug)
      );
      if (!valg) { ok = false; break; }
      plan[i] = valg;
      brukt.add(valg.slug);
    }
    if (!ok) continue;

    // 2) Fyll resten av uken uten gjentakelser.
    for (let i = 0; i < DAGER.length && ok; i++) {
      if (plan[i]) continue;
      const valg =
        bland(kandidater(DAGER[i], sesong, { utenFisk: true }), rnd).find((r) => !brukt.has(r.slug)) ||
        bland(kandidater(DAGER[i], sesong), rnd).find((r) => !brukt.has(r.slug));
      if (!valg) { ok = false; break; }
      plan[i] = valg;
      brukt.add(valg.slug);
    }

    if (ok && plan.every(Boolean)) return plan;
  }

  // Nødløsning hvis det er for få retter til å fylle en hel uke.
  return DAGER.map((dag) => bland(kandidater(dag, sesongNa()), tilfeldig)[0] || null);
}

function byttDag(indeks) {
  const sesong = sesongNa();
  const dag = DAGER[indeks];
  const navaerende = uke[indeks];
  const andreSlugs = new Set(uke.filter((r, i) => r && i !== indeks).map((r) => r.slug));
  const antallFisk = uke.filter((r) => r && erFisk(r)).length;
  const maBeholdeFisk = navaerende && erFisk(navaerende) && antallFisk <= MIN_FISK;

  const valg =
    bland(kandidater(dag, sesong, { kunFisk: maBeholdeFisk }), tilfeldig).find(
      (r) => !andreSlugs.has(r.slug) && r.slug !== navaerende?.slug
    ) ||
    bland(retter.filter((r) => passerDag(r, dag) && (!maBeholdeFisk || erFisk(r))), tilfeldig).find(
      (r) => !andreSlugs.has(r.slug) && r.slug !== navaerende?.slug
    );

  if (valg) {
    uke[indeks] = valg;
    tegnUke();
  }
}

/* ---------- visning ---------- */

function merker(rett) {
  const biter = [];
  if (erFisk(rett)) biter.push('<span class="merke merke--fisk">Fisk</span>');
  if (rett.anledning.includes("helg") && !rett.anledning.includes("hverdag")) {
    biter.push('<span class="merke">Helg</span>');
  }
  return biter.join("");
}

function metatekst(rett) {
  return [rett.tid, rett.beskrivelse].filter(Boolean).join(" · ");
}

function tegnUke() {
  const liste = el("uke-liste");
  liste.innerHTML = "";

  uke.forEach((rett, i) => {
    const dag = DAGER[i];
    const li = document.createElement("li");
    li.className = "dag" + (dag.anledning === "helg" ? " dag--helg" : "");
    li.innerHTML = `
      <span class="dag__navn">${dag.navn}</span>
      <button type="button" class="dag__rett" data-slug="${rett ? rett.slug : ""}">
        ${merker(rett || { kategori: "", anledning: [] })}${rett ? rett.navn : "Ingen passende rett"}
        <span class="dag__meta">${rett ? metatekst(rett) : ""}</span>
      </button>
      <button type="button" class="bytt" data-dag="${i}">Bytt</button>`;
    liste.appendChild(li);
  });

  const antallFisk = uke.filter((r) => r && erFisk(r)).length;
  el("fisk-status").textContent = `${antallFisk} fiskedager denne uken · trykk på en rett for oppskriften`;
}

function tegnAlle(filter = "alle") {
  const beholder = el("alle-liste");
  beholder.innerHTML = "";
  const utvalg = retter
    .filter((r) =>
      filter === "alle" ||
      r.kategori === filter ||
      r.anledning.includes(filter) ||
      r.sesong.includes(filter)
    )
    .sort((a, b) => a.navn.localeCompare(b.navn, "nb"));

  for (const rett of utvalg) {
    const kort = document.createElement("button");
    kort.type = "button";
    kort.className = "kort";
    kort.dataset.slug = rett.slug;
    kort.innerHTML = `
      <div>${merker(rett)}</div>
      <h3>${rett.navn}</h3>
      <p>${metatekst(rett)}</p>`;
    beholder.appendChild(kort);
  }
}

function visOppskrift(slug) {
  const rett = retter.find((r) => r.slug === slug);
  if (!rett) return;
  const sesonger = rett.sesong.map((s) => SESONGNAVN[s] || "Hele året").join(", ");
  el("dialog-innhold").innerHTML = `
    <div>${merker(rett)}</div>
    <h2>${rett.navn}</h2>
    <p class="dialog-meta">
      ${[rett.tid, rett.porsjoner ? rett.porsjoner + " porsjoner" : "", sesonger].filter(Boolean).join(" · ")}
    </p>
    ${rett.beskrivelse ? `<p>${rett.beskrivelse}</p>` : ""}
    ${rett.oppskrift}`;
  el("oppskrift-dialog").showModal();
}

/* ---------- oppstart ---------- */

function nyUke(fast = false) {
  const sesong = sesongNa();
  const rnd = fast ? froRandom(new Date().getFullYear() * 100 + ukenummer()) : tilfeldig;
  uke = lagUke(rnd, sesong);
  tegnUke();
}

async function start() {
  try {
    const svar = await fetch("data/retter.json", { cache: "no-cache" });
    if (!svar.ok) throw new Error(svar.status);
    retter = await svar.json();
  } catch (e) {
    el("feil").textContent = "Fikk ikke lest inn rettene (data/retter.json). Kjør python3 bygg.py.";
    el("feil").classList.remove("skjult");
    return;
  }

  const sesong = sesongNa();
  el("sesong-merke").textContent = `${SESONGNAVN[sesong]} · uke ${ukenummer()}`;
  el("uke-tekst").textContent = `Forslag til uke ${ukenummer()} – minst ${MIN_FISK} dager med fisk.`;

  nyUke(true);

  const filtre = [
    ["alle", "Alle"],
    ["fisk", "Fisk"],
    ["kjott", "Kjøtt"],
    ["kylling", "Kylling"],
    ["hverdag", "Hverdag"],
    ["helg", "Helg"],
    ["sommer", "Sommer"],
    ["host", "Høst"],
  ];
  el("filtre").innerHTML = filtre
    .map(
      ([verdi, tekst], i) =>
        `<button type="button" class="knapp" data-filter="${verdi}" aria-pressed="${i === 0}">${tekst}</button>`
    )
    .join("");
  tegnAlle();

  el("ny-uke").addEventListener("click", () => nyUke(false));

  el("vis-alle").addEventListener("click", () => {
    const seksjon = el("alle");
    const skjult = seksjon.classList.toggle("skjult");
    el("vis-alle").textContent = skjult ? "Vis alle" : "Skjul alle";
    if (!skjult) seksjon.scrollIntoView({ behavior: "smooth", block: "start" });
  });

  el("filtre").addEventListener("click", (e) => {
    const knapp = e.target.closest("[data-filter]");
    if (!knapp) return;
    for (const b of el("filtre").children) b.setAttribute("aria-pressed", b === knapp);
    tegnAlle(knapp.dataset.filter);
  });

  document.addEventListener("click", (e) => {
    const bytt = e.target.closest(".bytt");
    if (bytt) return byttDag(Number(bytt.dataset.dag));
    const rett = e.target.closest("[data-slug]");
    if (rett && rett.dataset.slug) visOppskrift(rett.dataset.slug);
  });

  el("lukk-dialog").addEventListener("click", () => el("oppskrift-dialog").close());
  el("oppskrift-dialog").addEventListener("click", (e) => {
    if (e.target.id === "oppskrift-dialog") el("oppskrift-dialog").close();
  });
}

start();
