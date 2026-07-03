// IB Dream — demo UI. All numbers come from the backend /dream/demo endpoint.
// This script only renders what the API returns; it never calculates milestones.

(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const btn = $("calcBtn");
  const depositBtn = $("depositBtn");
  const results = $("results");
  const errorMsg = $("errorMsg");

  let lastVisible = null; // to detect when the dream becomes "more real"
  const inputIds = [
    "dream_name",
    "target_amount",
    "current_saved_amount",
    "monthly_contribution",
    "deposit_amount",
];

  const setBusy = (busy) => {
    // Lock the form while a request is in flight: button truly disabled,
    // inputs read-only, spinner shown. Everything re-enables when done.
    btn.disabled = busy;
    depositBtn.disabled = busy;

    btn.classList.toggle("is-loading", busy);
    depositBtn.classList.toggle("is-loading", busy);
    
    inputIds.forEach((id) => { $(id).readOnly = busy; });
  };

  const fmtINR = (value) => {
    // Indian grouping, no decimals for whole rupees. value may be a string like "2400000.00".
    const n = Math.round(Number(value));
    return "₹" + n.toLocaleString("en-IN");
  };

  const buildPayload = () => ({
    dream_name: $("dream_name").value.trim() || "My Dream",
    target_amount: Number($("target_amount").value),
    current_saved_amount: Number($("current_saved_amount").value),
    monthly_contribution: Number($("monthly_contribution").value),
  });
  const buildDepositPayload = () => ({
    dream_name: $("dream_name").value.trim() || "My Dream",

    target_amount: Number($("target_amount").value),

    current_saved_amount: Number($("current_saved_amount").value),

    monthly_contribution: Number($("monthly_contribution").value),

    deposit_amount: Number($("deposit_amount").value),
});

  const dreamEmoji = (name) => {
    const n = (name || "").toLowerCase();
    if (n.includes("porsche") || n.includes("car") || n.includes("bmw") || n.includes("audi")) return "🚗";
    if (n.includes("bike") || n.includes("activa") || n.includes("scooter")) return "🛵";
    if (n.includes("home") || n.includes("house") || n.includes("flat")) return "🏡";
    if (n.includes("trip") || n.includes("travel") || n.includes("goa") || n.includes("europe")) return "✈️";
    if (n.includes("laptop") || n.includes("phone") || n.includes("mac")) return "💻";
    return "🌟";
  };

  const cardsHTML = (d) => {
    const items = [
      { label: "Progress", value: `${d.progress_pct}<small>%</small>`, accent: true },
      { label: "Visible", value: `${d.visible_pct}<small>%</small>`, accent: true },
      { label: "Milestones", value: d.steps },
      { label: "Current step", value: `${d.current_step}<small> / ${d.steps}</small>` },
      { label: "Next unlock", value: d.next_step ? `Step ${d.next_step}` : "Done", },
      { label: "Remaining", value: fmtINR(d.gap_to_next) },
      { label: "ETA next", value: d.months_to_next_unlock != null ? `${d.months_to_next_unlock}` : "—", sub: "months" },
      { label: "ETA full dream", value: d.months_to_full_dream != null ? `${d.months_to_full_dream}` : "—", sub: "months" },
    ];
    return items.map((it, i) => `
      <div class="card ${it.accent ? "card--accent" : ""}" style="animation-delay:${i * 55}ms">
        <div class="card__label">${it.label}</div>
        <div class="card__value">${it.value}</div>
        ${it.sub ? `<div class="card__sub">${it.sub}</div>` : ""}
      </div>`).join("");
  };

  const milestonesHTML = (d) => {
    let html = "";
    for (let i = 1; i <= d.steps; i++) {
      const unlocked = i <= d.current_step;
      const isNext = i === d.next_step;
      const cls = unlocked ? "ms ms--on" : isNext ? "ms ms--next" : "ms";
      const glyph = unlocked ? "✓" : i;
      html += `
        <div class="${cls}" style="--i:${i - 1}">
          <div class="ms__dot">${glyph}</div>
          <div class="ms__num">${i}</div>
        </div>`;
    }
    return html;
  };

  const render = (d) => {
    $("dreamTitle").textContent = `${dreamEmoji(d.dream)}  ${d.dream}`;
    updatePreview(d);
    const paceText = document.getElementById("paceText");
const nextEta = document.getElementById("nextEta");
const fullEta = document.getElementById("fullEta");
const nudgeBox = document.getElementById("nudgeBox");

if (d.pace) {
    paceText.textContent = d.pace.pace;

    nextEta.textContent =
        d.pace.months_next != null
            ? `${d.pace.months_next} months`
            : "—";

    fullEta.textContent =
        d.pace.months_full != null
            ? `${d.pace.months_full} months`
            : "—";
} else {
    paceText.textContent = "—";
    nextEta.textContent = "—";
    fullEta.textContent = "—";
}

nudgeBox.textContent =
    d.nudge || "Keep saving consistently!";

    // "becoming real" cue when visibility rises vs the previous run
    const becoming = $("becomingReal");
    if (lastVisible !== null && d.visible_pct > lastVisible) {
      becoming.hidden = false;
      clearTimeout(becoming._t);
      becoming._t = setTimeout(() => (becoming.hidden = true), 3200);
    } else {
      becoming.hidden = true;
    }
    lastVisible = d.visible_pct;

    $("cards").innerHTML = cardsHTML(d);
    $("ladderCount").textContent = `${d.current_step} of ${d.steps} unlocked`;
    $("progressVal").textContent = `${d.progress_pct}%`;
    $("visibleVal").textContent = `${d.visible_pct}%`;
    $("milestones").innerHTML = milestonesHTML(d);

    results.hidden = false;

    // animate bars after the layout paints (so width transition fires)
    requestAnimationFrame(() => requestAnimationFrame(() => {
      $("progressFill").style.width = `${Math.min(100, d.progress_pct)}%`;
      $("visibleFill").style.width = `${Math.min(100, d.visible_pct)}%`;
    }));
  };

  const calculate = async () => {
    errorMsg.hidden = true;
    setBusy(true);
    try {
      let res;
      try {
        res = await fetch("/dream/demo", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(buildPayload()),
        });
      } catch (networkErr) {
        throw new Error("Can't reach the IB Dream backend. Make sure the server is running, then try again.");
      }
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail?.[0]?.msg || detail.detail || `Request failed (${res.status})`);
      }
      const data = await res.json();
      render(data);
    } catch (err) {
      errorMsg.textContent = String(err.message || err);
      errorMsg.hidden = false;
    } finally {
      setBusy(false);
    }
  };
  const depositMoney = async () => {

    errorMsg.hidden = true;

    setBusy(true);

    try {

        const res = await fetch("/dream/deposit", {

            method: "POST",

            headers: {
                "Content-Type": "application/json",
            },

            body: JSON.stringify(buildDepositPayload()),
        });

        if (!res.ok) {

            const detail = await res.json().catch(() => ({}));

            throw new Error(
                detail.detail || `Request failed (${res.status})`
            );
        }

        const data = await res.json();

        render({

    ...data.state,

    ...data.pace,

    pace: data.aipa_pace,

    nudge: data.nudge,

});

        const updatedSaved = Number(data.current_saved);

$("current_saved_amount").value = updatedSaved;
$("deposit_amount").value = "";

    } catch (err) {

        errorMsg.textContent = err.message;

        errorMsg.hidden = false;

    } finally {

        setBusy(false);

    }

};

  btn.addEventListener("click", calculate);
  depositBtn.addEventListener(
    "click",
    depositMoney
);
  // calculate once on load so the founder sees a populated screen immediately
  window.addEventListener("DOMContentLoaded", calculate);
})();

function updatePreview(d){
  console.log("==========");
  console.log("Preview function called");
  console.log(d);
  console.log(document.getElementById("dreamArt"));
  console.log(document.querySelector(".preview"));

    const art = document.getElementById("dreamArt");
    const pct = document.getElementById("previewPct");
    const hint = document.getElementById("previewHint");
    const card = document.querySelector(".preview");

    if(!art) return;

    const name = (d.dream || "").toLowerCase();

    let icon = "🌟";

    if(name.includes("car") || name.includes("porsche"))
        icon = "🚗";
    else if(name.includes("bike") || name.includes("activa"))
        icon = "🛵";
    else if(name.includes("house") || name.includes("home"))
        icon = "🏡";
    else if(name.includes("travel"))
        icon = "✈️";
    else if(name.includes("laptop"))
        icon = "💻";

    art.textContent = icon;

    const v = Number(d.visible_pct || 0);

    pct.textContent = v.toFixed(1) + "%";

    const opacity = 0.12 + (v/100)*0.88;

    const blur = 9 - (v/100)*9;

    art.style.opacity = opacity;
    art.style.filter = `blur(${blur}px)`;

    if(v >= 60){
        card.classList.add("real");
        hint.textContent = "Dream becoming real ✨";
    }else{
        card.classList.remove("real");
        hint.textContent = "Save more to bring it into focus";
    }
}
