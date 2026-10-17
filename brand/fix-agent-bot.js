// Freitags Fix Agent mascot: a little repair bot eating pizza.
// Time-driven (no CSS animations) so the demo video can render it frame by frame:
//   const bot = FixBot.create(svgElement); bot.render(tSeconds);
// One loop is 5 s: lift slice -> three bites -> pull the wrench from the tool belt -> fix the slice (sparkles)
// -> wrench back on the belt -> idle bob.
(function (global) {
  const NS = "http://www.w3.org/2000/svg";
  const C = { ink: "#2b1d14", shell: "#f6efe3", screen: "#17120f", amber: "#e9b45f", red: "#c8102e",
              cheese: "#ffd36b", crust: "#d9973f", pep: "#b8322a", cheek: "#f4a3a8",
              belt: "#6b4423", steel: "#9aa5b1" };
  const LOOP = 5;
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const ease = x => { x = clamp(x); return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
  const lerp = (a, b, k) => a + (b - a) * k;

  const MARKUP = `
  <defs>
    <mask id="ID-bites" maskUnits="userSpaceOnUse" x="-20" y="-60" width="120" height="120">
      <rect x="-20" y="-60" width="120" height="120" fill="#fff"/>
      <circle id="ID-b1" cx="-2" cy="-7" r="0" fill="#000"/>
      <circle id="ID-b2" cx="0" cy="9" r="0" fill="#000"/>
      <circle id="ID-b3" cx="13" cy="0" r="0" fill="#000"/>
    </mask>
    <radialGradient id="ID-glow"><stop offset="0" stop-color="${C.amber}" stop-opacity=".9"/><stop offset="1" stop-color="${C.amber}" stop-opacity="0"/></radialGradient>
  </defs>
  <g id="ID-all">
    <ellipse id="ID-shadow" cx="200" cy="352" rx="78" ry="10" fill="#000" opacity=".18"/>
    <g id="ID-body">
      <circle id="ID-halo" cx="200" cy="34" r="22" fill="url(#ID-glow)"/>
      <line x1="200" y1="72" x2="200" y2="42" stroke="${C.ink}" stroke-width="6" stroke-linecap="round"/>
      <circle id="ID-bulb" cx="200" cy="36" r="9" fill="${C.amber}" stroke="${C.ink}" stroke-width="4"/>
      <!-- torso -->
      <rect x="140" y="214" width="120" height="104" rx="28" fill="${C.red}" stroke="${C.ink}" stroke-width="6"/>
      <circle cx="200" cy="262" r="24" fill="${C.amber}" stroke="${C.ink}" stroke-width="5"/>
      <path d="M190 252 a8 8 0 1 0 11 11 l10 10 a4 4 0 0 0 6 -6 l-10 -10 a8 8 0 0 0 -11 -11 l5 5 -2 6 -6 2z" fill="${C.ink}"/>
      <!-- tool belt: wrench (left pouch) and screwdriver (right pouch) -->
      <g id="ID-wrench-belt" transform="translate(163 304)"><g id="ID-wb"><rect x="-5" y="-40" width="10" height="42" rx="5" fill="${C.steel}" stroke="${C.ink}" stroke-width="4"/>
        <path d="M-13 -40 a14 14 0 1 1 26 0 l-6 0 l0 -10 l-14 0 l0 10 z" fill="${C.steel}" stroke="${C.ink}" stroke-width="4" stroke-linejoin="round"/></g></g>
      <g transform="translate(236 300)"><rect x="-3" y="-14" width="6" height="20" fill="${C.steel}" stroke="${C.ink}" stroke-width="3"/>
        <rect x="-7" y="-38" width="14" height="26" rx="6" fill="${C.amber}" stroke="${C.ink}" stroke-width="4"/>
        <line x1="-2" y1="-33" x2="-2" y2="-18" stroke="${C.ink}" stroke-width="2" opacity=".5"/></g>
      <rect x="136" y="290" width="128" height="16" rx="6" fill="${C.belt}" stroke="${C.ink}" stroke-width="5"/>
      <rect x="192" y="289" width="16" height="18" rx="3" fill="${C.amber}" stroke="${C.ink}" stroke-width="4"/>
      <path d="M150 300 h26 v22 a6 6 0 0 1 -6 6 h-14 a6 6 0 0 1 -6 -6 z" fill="${C.belt}" stroke="${C.ink}" stroke-width="5"/>
      <path d="M224 300 h24 v20 a6 6 0 0 1 -6 6 h-12 a6 6 0 0 1 -6 -6 z" fill="${C.belt}" stroke="${C.ink}" stroke-width="5"/>
      <rect x="160" y="318" width="22" height="26" rx="8" fill="${C.shell}" stroke="${C.ink}" stroke-width="5"/>
      <rect x="218" y="318" width="22" height="26" rx="8" fill="${C.shell}" stroke="${C.ink}" stroke-width="5"/>
      <!-- head -->
      <rect x="96" y="112" width="20" height="44" rx="8" fill="${C.amber}" stroke="${C.ink}" stroke-width="5"/>
      <rect x="284" y="112" width="20" height="44" rx="8" fill="${C.amber}" stroke="${C.ink}" stroke-width="5"/>
      <rect x="110" y="72" width="180" height="140" rx="38" fill="${C.shell}" stroke="${C.ink}" stroke-width="6"/>
      <rect x="132" y="94" width="136" height="94" rx="26" fill="${C.screen}"/>
      <g id="ID-eyes-open"><rect id="ID-el" x="160" y="114" width="22" height="28" rx="11" fill="${C.amber}"/>
        <rect id="ID-er" x="218" y="114" width="22" height="28" rx="11" fill="${C.amber}"/></g>
      <g id="ID-eyes-happy" fill="none" stroke="${C.amber}" stroke-width="7" stroke-linecap="round">
        <path d="M159 134 q12 -16 24 0"/><path d="M217 134 q12 -16 24 0"/></g>
      <ellipse id="ID-mouth" cx="200" cy="164" rx="16" ry="4" fill="${C.red}"/>
      <circle id="ID-ckl" cx="146" cy="168" r="8" fill="${C.cheek}" opacity="0"/>
      <circle id="ID-ckr" cx="254" cy="168" r="8" fill="${C.cheek}" opacity="0"/>
    </g>
    <!-- left arm (moves to the tool belt and back) -->
    <line id="ID-larm-o" x1="146" y1="244" x2="112" y2="292" stroke="${C.ink}" stroke-width="26" stroke-linecap="round"/>
    <line id="ID-larm" x1="146" y1="244" x2="112" y2="292" stroke="${C.shell}" stroke-width="16" stroke-linecap="round"/>
    <g id="ID-wrench-hand"><g id="ID-wh"><rect x="-5" y="-40" width="10" height="42" rx="5" fill="${C.steel}" stroke="${C.ink}" stroke-width="4"/>
        <path d="M-13 -40 a14 14 0 1 1 26 0 l-6 0 l0 -10 l-14 0 l0 10 z" fill="${C.steel}" stroke="${C.ink}" stroke-width="4" stroke-linejoin="round"/></g></g>
    <circle id="ID-lhand" cx="112" cy="292" r="13" fill="${C.shell}" stroke="${C.ink}" stroke-width="5"/>
    <!-- right arm + slice (drawn on top) -->
    <line id="ID-rarm-o" x1="254" y1="246" x2="300" y2="280" stroke="${C.ink}" stroke-width="26" stroke-linecap="round"/>
    <line id="ID-rarm" x1="254" y1="246" x2="300" y2="280" stroke="${C.shell}" stroke-width="16" stroke-linecap="round"/>
    <g id="ID-slice">
      <g mask="url(#ID-bites)">
        <path d="M0 0 L66 -30 L66 30 Z" fill="${C.cheese}" stroke="${C.ink}" stroke-width="5" stroke-linejoin="round"/>
        <circle cx="34" cy="-8" r="7" fill="${C.pep}"/><circle cx="50" cy="12" r="7" fill="${C.pep}"/><circle cx="22" cy="6" r="5" fill="${C.pep}"/>
      </g>
      <rect x="60" y="-34" width="18" height="68" rx="9" fill="${C.crust}" stroke="${C.ink}" stroke-width="5"/>
    </g>
    <circle id="ID-hand" cx="300" cy="280" r="13" fill="${C.shell}" stroke="${C.ink}" stroke-width="5"/>
    <g id="ID-crumbs" fill="${C.crust}"></g>
    <g id="ID-sparks" fill="${C.amber}"></g>
  </g>`;

  const STAR = "M0 -11 L3 -3 L11 0 L3 3 L0 11 L-3 3 L-11 0 L-3 -3 Z";

  function create(svg, id = "fb") {
    svg.setAttribute("viewBox", "0 0 400 380");
    svg.innerHTML = MARKUP.replace(/ID-/g, id + "-");
    const $ = s => svg.querySelector("#" + id + "-" + s);
    const crumbs = Array.from({ length: 6 }, (_, i) => {
      const c = document.createElementNS(NS, "circle"); c.setAttribute("r", 3 + (i % 3)); $("crumbs").appendChild(c); return c; });
    const sparks = Array.from({ length: 5 }, () => {
      const p = document.createElementNS(NS, "path"); p.setAttribute("d", STAR); $("sparks").appendChild(p); return p; });

    function render(time) {
      const u = ((time % LOOP) + LOOP) % LOOP;
      // pose: 0 = resting (slice held up), 1 = slice at the mouth
      const pose = u < 0.7 ? ease(u / 0.7) : u < 1.6 ? 1 : 1 - ease((u - 1.6) / 0.6);
      const chomps = [0.7, 1.0, 1.3];
      let open = 0, nudge = 0;
      chomps.forEach(c => { const k = (u - c) / 0.3; if (k >= 0 && k < 1) { open = Math.sin(k * Math.PI); nudge = open; } });
      const bob = Math.sin(time * Math.PI) * 3;                     // gentle idle bob, whole bot
      $("all").setAttribute("transform", `translate(0 ${bob.toFixed(2)})`);
      $("shadow").setAttribute("rx", (78 - bob).toFixed(1));

      // slice: tip position and rotation between rest and eat poses
      const tipX = lerp(318, 212 + nudge * 6, pose), tipY = lerp(206, 166, pose), rot = lerp(90, 0, pose);
      $("slice").setAttribute("transform", `translate(${tipX.toFixed(1)} ${tipY.toFixed(1)}) rotate(${rot.toFixed(1)})`);
      const a = rot * Math.PI / 180, hx = tipX + Math.cos(a) * 80, hy = tipY + Math.sin(a) * 80;
      ["rarm", "rarm-o"].forEach(k => { $(k).setAttribute("x2", hx.toFixed(1)); $(k).setAttribute("y2", hy.toFixed(1)); });
      $("hand").setAttribute("cx", hx.toFixed(1)); $("hand").setAttribute("cy", hy.toFixed(1));

      // left hand: rest -> tool belt (grab wrench) -> up to the slice -> twist -> back to the belt -> rest
      const REST = [112, 292], BELT = [163, 312], WORK = [262, 262];
      const seg = (a, b, k) => [lerp(a[0], b[0], ease(k)), lerp(a[1], b[1], ease(k))];
      let lh = REST, holding = false;
      if (u >= 2.0 && u < 2.4) lh = seg(REST, BELT, (u - 2.0) / 0.4);
      else if (u >= 2.4 && u < 2.9) { lh = seg(BELT, WORK, (u - 2.4) / 0.5); holding = true; }
      else if (u >= 2.9 && u < 3.7) { lh = WORK; holding = true; }
      else if (u >= 3.7 && u < 4.2) { lh = seg(WORK, BELT, (u - 3.7) / 0.5); holding = true; }
      else if (u >= 4.2 && u < 4.6) lh = seg(BELT, REST, (u - 4.2) / 0.4);
      else if (u < 2.0 || u >= 4.6) { const sway = Math.sin(time * 2) * 5; lh = [REST[0] + sway, REST[1] - Math.abs(sway) * 0.4]; }
      ["larm", "larm-o"].forEach(k => { $(k).setAttribute("x2", lh[0].toFixed(1)); $(k).setAttribute("y2", lh[1].toFixed(1)); });
      $("lhand").setAttribute("cx", lh[0].toFixed(1)); $("lhand").setAttribute("cy", lh[1].toFixed(1));
      const twist = u >= 2.9 && u < 3.7 ? Math.sin((u - 2.9) / 0.8 * Math.PI * 4) * 28 : 0;
      const tilt = holding ? 40 + twist : 0;
      $("wrench-belt").style.display = holding ? "none" : "";
      $("wrench-hand").style.display = holding ? "" : "none";
      $("wrench-hand").setAttribute("transform", `translate(${lh[0].toFixed(1)} ${lh[1].toFixed(1)}) rotate(${tilt.toFixed(1)})`);

      // bites appear on each chomp, and the wrench "fixes" the slice (bites heal) at 3.0-3.6 s
      const heal = clamp((u - 3.0) / 0.6);
      ["b1", "b2", "b3"].forEach((b, i) => {
        const grown = clamp((u - (chomps[i] + 0.15)) / 0.08);
        $(b).setAttribute("r", (13 * grown * (1 - heal)).toFixed(1)); });

      $("mouth").setAttribute("ry", (4 + open * 11).toFixed(1));
      $("mouth").setAttribute("rx", (16 + open * 2).toFixed(1));

      // eyes: happy (^ ^) while chewing and after, quick blink at 3.6 s
      const happy = u >= 0.75 && u < 1.9 || u >= 3.2 && u < 4.2;
      $("eyes-open").style.display = happy ? "none" : "";
      $("eyes-happy").style.display = happy ? "" : "none";
      const blink = u > 4.7 && u < 4.85 ? 0.15 : 1;
      ["el", "er"].forEach(k => { $(k).setAttribute("height", (28 * blink).toFixed(1)); $(k).setAttribute("y", (128 - 14 * blink).toFixed(1)); });
      const cheek = Math.max(clamp(Math.min((u - 0.8) / 0.3, (1.9 - u) / 0.3)), clamp(Math.min((u - 3.2) / 0.3, (4.2 - u) / 0.3)));
      $("ckl").setAttribute("opacity", (cheek * 0.8).toFixed(2)); $("ckr").setAttribute("opacity", (cheek * 0.8).toFixed(2));

      // antenna glows on bites and when the fix happens
      const glow = Math.max(open, heal > 0 && heal < 1 ? 1 : 0, 0.35 + 0.15 * Math.sin(time * 4));
      $("halo").setAttribute("opacity", glow.toFixed(2)); $("halo").setAttribute("r", (16 + glow * 10).toFixed(1));


      // crumbs fall from the mouth after each bite
      crumbs.forEach((c, i) => {
        const start = chomps[i % 3] + 0.2, k = (u - start) / 0.9;
        if (k < 0 || k > 1) { c.setAttribute("opacity", 0); return; }
        const dx = (i % 2 ? 1 : -1) * (6 + i * 4) * k;
        c.setAttribute("cx", (200 + dx).toFixed(1)); c.setAttribute("cy", (172 + 150 * k * k).toFixed(1));
        c.setAttribute("opacity", (1 - k).toFixed(2)); });

      // sparkles around the slice while it heals
      sparks.forEach((s, i) => {
        const k = (u - 3.0 - i * 0.08) / 0.6;
        if (k < 0 || k > 1) { s.setAttribute("opacity", 0); return; }
        const ang = i * 72 * Math.PI / 180, r = 38 + 22 * k;
        const cx = 318 + Math.cos(ang) * r, cy = 236 + Math.sin(ang) * r;
        s.setAttribute("transform", `translate(${cx.toFixed(1)} ${cy.toFixed(1)}) scale(${Math.sin(k * Math.PI).toFixed(2)})`);
        s.setAttribute("opacity", Math.sin(k * Math.PI).toFixed(2)); });
    }
    render(0);
    return { render, LOOP };
  }
  global.FixBot = { create, LOOP };
})(window);
