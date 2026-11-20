// Türk alfabesi kartlarının resimleri: elle yazılmış vektör çizimler (200×200 tuval).
// Her resim aynı çizgi kalınlığını ve aynı renk takımını kullanır; dışarıdan görsel alınmaz.
'use strict';

const R = {
  murekkep: '#3A2E39', kirmizi: '#E8544E', turuncu: '#F39C38', sari: '#F7C948', koyuSari: '#E0A92E',
  yesil: '#6BB86A', koyuYesil: '#3F8F5A', mavi: '#4A90D9', acikMavi: '#BFE3F5', pembe: '#F4A6B8',
  koyuPembe: '#D9708A', kahve: '#A0673C', koyuKahve: '#6E4426', gri: '#B8BFCB', koyuGri: '#8A94A6',
  beyaz: '#FFFFFF', krem: '#FFF4DC', mor: '#8E5BB5', acikMor: '#B88AD9',
};
const yanak = (x, y) => `<ellipse cx="${x}" cy="${y}" rx="7" ry="4.5" fill="${R.pembe}" stroke="none" opacity=".85"/>`;
const goz = (x, y, r = 6) => `<circle cx="${x}" cy="${y}" r="${r}" fill="${R.murekkep}" stroke="none"/><circle cx="${x + r * 0.35}" cy="${y - r * 0.35}" r="${r * 0.33}" fill="#fff" stroke="none"/>`;
const parilti = (x, y, s = 1) => `<path d="M${x} ${y - 9 * s} L${x + 2.5 * s} ${y - 2.5 * s} L${x + 9 * s} ${y} L${x + 2.5 * s} ${y + 2.5 * s} L${x} ${y + 9 * s} L${x - 2.5 * s} ${y + 2.5 * s} L${x - 9 * s} ${y} L${x - 2.5 * s} ${y - 2.5 * s} Z" fill="${R.sari}" stroke="none"/>`;
function yildizYolu(cx, cy, dis, ic, uc = 5) {
  const n = [];
  for (let i = 0; i < uc * 2; i++) {
    const a = -Math.PI / 2 + (i * Math.PI) / uc, r = i % 2 ? ic : dis;
    n.push((cx + r * Math.cos(a)).toFixed(1) + ' ' + (cy + r * Math.sin(a)).toFixed(1));
  }
  return 'M' + n.join(' L') + ' Z';
}

const RESIMLER = {
  ari: () => `
    <ellipse cx="78" cy="66" rx="24" ry="32" fill="#E6F5FC" transform="rotate(-28 78 66)"/>
    <ellipse cx="120" cy="62" rx="22" ry="30" fill="#E6F5FC" transform="rotate(22 120 62)"/>
    <path d="M154 120 L180 116 L158 134 Z" fill="${R.murekkep}"/>
    <clipPath id="ari-g"><ellipse cx="102" cy="122" rx="58" ry="44"/></clipPath>
    <ellipse cx="102" cy="122" rx="58" ry="44" fill="${R.sari}"/>
    <g clip-path="url(#ari-g)" stroke="none" fill="${R.murekkep}"><rect x="98" y="70" width="16" height="110"/><rect x="128" y="70" width="16" height="110"/></g>
    <ellipse cx="102" cy="122" rx="58" ry="44" fill="none"/>
    <path d="M62 84 Q54 64 44 56" fill="none"/><circle cx="42" cy="53" r="6" fill="${R.murekkep}"/>
    <path d="M78 80 Q78 62 86 50" fill="none"/><circle cx="88" cy="47" r="6" fill="${R.murekkep}"/>
    ${goz(64, 114)}${goz(84, 114)}${yanak(56, 130)}
    <path d="M66 134 Q74 141 82 134" fill="none"/>`,

  balik: () => `
    <path d="M146 100 L182 68 Q172 100 182 132 Z" fill="${R.turuncu}"/>
    <path d="M82 64 Q102 36 126 66 Z" fill="#E07F22"/>
    <path d="M90 136 Q104 158 118 134 Z" fill="#E07F22"/>
    <ellipse cx="96" cy="100" rx="60" ry="40" fill="${R.turuncu}"/>
    <path d="M104 84 q10 16 0 32 M124 86 q9 14 0 28 M84 86 q9 14 0 28" fill="none" stroke="#C9661A" stroke-width="4"/>
    <circle cx="62" cy="92" r="11" fill="#fff"/>${goz(64, 92, 6)}
    <path d="M42 110 Q50 117 58 110" fill="none"/>
    <circle cx="30" cy="62" r="7" fill="${R.acikMavi}"/><circle cx="42" cy="38" r="5" fill="${R.acikMavi}"/><circle cx="24" cy="30" r="4" fill="${R.acikMavi}"/>`,

  civciv: () => `
    <path d="M96 52 Q98 34 110 40 Q108 28 122 32" fill="none"/>
    <circle cx="100" cy="100" r="50" fill="${R.sari}"/>
    <path d="M140 104 Q162 104 158 126 Q140 128 134 114 Z" fill="${R.koyuSari}"/>
    ${goz(84, 92)}${goz(116, 92)}${yanak(74, 108)}${yanak(126, 108)}
    <path d="M90 104 L110 104 L100 118 Z" fill="${R.turuncu}"/>
    <path d="M40 132 L56 118 L70 134 L85 118 L100 134 L115 118 L130 134 L144 118 L160 132 Q160 182 100 182 Q40 182 40 132 Z" fill="#fff"/>
    <path d="M62 160 l8 -6 M128 154 l8 6" fill="none" stroke="${R.gri}" stroke-width="4"/>`,

  cilek: () => `
    <path d="M100 182 C54 162 38 112 50 86 C60 66 84 68 100 76 C116 68 140 66 150 86 C162 112 146 162 100 182 Z" fill="${R.kirmizi}"/>
    <g fill="#FFE08A" stroke="none">
      <ellipse cx="76" cy="100" rx="3.5" ry="5"/><ellipse cx="100" cy="98" rx="3.5" ry="5"/><ellipse cx="124" cy="100" rx="3.5" ry="5"/>
      <ellipse cx="66" cy="124" rx="3.5" ry="5"/><ellipse cx="90" cy="122" rx="3.5" ry="5"/><ellipse cx="112" cy="122" rx="3.5" ry="5"/><ellipse cx="134" cy="124" rx="3.5" ry="5"/>
      <ellipse cx="80" cy="146" rx="3.5" ry="5"/><ellipse cx="102" cy="146" rx="3.5" ry="5"/><ellipse cx="122" cy="146" rx="3.5" ry="5"/><ellipse cx="100" cy="166" rx="3.5" ry="5"/>
    </g>
    <path d="M100 80 L74 64 L92 64 L84 46 L100 58 L116 46 L108 64 L126 64 Z" fill="${R.yesil}"/>
    <path d="M100 58 Q100 40 108 30" fill="none" stroke-width="6"/>`,

  dondurma: () => `
    <path d="M66 104 L134 104 L100 186 Z" fill="#E8B66A"/>
    <path d="M78 116 L110 160 M96 112 L120 140 M122 116 L90 160 M104 112 L80 140" fill="none" stroke="#C48A3C" stroke-width="4"/>
    <circle cx="100" cy="96" r="36" fill="${R.pembe}"/>
    <path d="M66 104 Q72 118 80 106 Q88 120 96 106 Q104 120 112 106 Q120 120 128 106 Q132 112 134 104" fill="${R.pembe}"/>
    <circle cx="100" cy="58" r="30" fill="${R.krem}"/>
    <circle cx="104" cy="26" r="11" fill="${R.kirmizi}"/>
    <path d="M106 16 Q110 6 120 4" fill="none" stroke-width="4"/>
    <g fill="none" stroke-width="4"><path d="M84 48 l4 3"/><path d="M110 64 l5 -2"/><path d="M80 90 l4 4"/><path d="M118 88 l5 -3"/></g>`,

  elma: () => `
    <path d="M100 64 C80 48 38 52 38 100 C38 148 70 180 100 168 C130 180 162 148 162 100 C162 52 120 48 100 64 Z" fill="${R.kirmizi}"/>
    <path d="M100 64 Q102 42 112 30" fill="none" stroke="${R.koyuKahve}" stroke-width="7"/>
    <path d="M106 50 Q126 30 148 42 Q128 62 106 50 Z" fill="${R.yesil}"/>
    <ellipse cx="68" cy="94" rx="8" ry="15" fill="#fff" stroke="none" opacity=".55" transform="rotate(20 68 94)"/>`,

  fil: () => `
    <rect x="78" y="130" width="24" height="50" rx="8" fill="${R.gri}"/>
    <rect x="132" y="130" width="24" height="50" rx="8" fill="${R.gri}"/>
    <path d="M170 104 Q186 112 180 132" fill="none"/>
    <ellipse cx="118" cy="114" rx="56" ry="44" fill="${R.gri}"/>
    <path d="M40 98 Q26 136 38 162 Q46 172 54 160 Q46 138 58 112 Z" fill="${R.gri}"/>
    <circle cx="66" cy="92" r="36" fill="${R.gri}"/>
    <ellipse cx="96" cy="92" rx="24" ry="32" fill="${R.gri}"/>
    <ellipse cx="98" cy="94" rx="13" ry="20" fill="${R.pembe}" stroke="none"/>
    ${goz(58, 84)}${yanak(52, 104)}
    <path d="M44 120 q-8 4 -6 12" fill="none" stroke-width="3" stroke="${R.koyuGri}"/>`,

  gemi: () => `
    <path d="M118 56 q-6 -12 6 -16 q2 -14 18 -10 q12 -8 20 4" fill="none" stroke="${R.koyuGri}" stroke-width="5"/>
    <rect x="110" y="56" width="24" height="38" fill="${R.sari}"/>
    <rect x="110" y="56" width="24" height="10" fill="${R.kirmizi}"/>
    <rect x="56" y="86" width="88" height="36" rx="4" fill="#fff"/>
    <circle cx="76" cy="104" r="7" fill="${R.acikMavi}"/><circle cx="100" cy="104" r="7" fill="${R.acikMavi}"/><circle cx="124" cy="104" r="7" fill="${R.acikMavi}"/>
    <path d="M24 122 L176 122 L154 162 L46 162 Z" fill="${R.kirmizi}"/>
    <path d="M34 138 L168 138" fill="none" stroke="#fff" stroke-width="7"/>
    <path d="M14 172 q16 -12 32 0 t32 0 t32 0 t32 0 t32 0 t32 0" fill="none" stroke="${R.mavi}" stroke-width="6"/>`,

  dag: () => `
    <circle cx="158" cy="46" r="20" fill="${R.sari}"/>
    <path d="M86 170 L140 84 L194 170 Z" fill="#7F8DAA"/>
    <path d="M140 84 L126 106 L136 102 L144 110 L152 100 Z" fill="#fff"/>
    <path d="M10 170 L82 46 L154 170 Z" fill="#96A3BE"/>
    <path d="M82 46 L62 80 L74 74 L84 86 L94 72 L104 80 Z" fill="#fff"/>
    <path d="M4 170 Q100 158 196 170 L196 184 L4 184 Z" fill="${R.yesil}"/>`,

  horoz: () => `
    <path d="M138 108 Q176 72 164 34 Q150 72 128 98 Z" fill="${R.koyuYesil}"/>
    <path d="M140 116 Q186 98 190 62 Q166 96 134 110 Z" fill="${R.mavi}"/>
    <path d="M138 126 Q182 128 194 100 Q170 120 132 118 Z" fill="${R.kirmizi}"/>
    <path d="M86 150 L80 182 M80 182 l-12 2 M80 182 l12 0 M114 150 L120 182 M120 182 l-12 0 M120 182 l12 2" fill="none" stroke="${R.turuncu}" stroke-width="6"/>
    <ellipse cx="100" cy="124" rx="46" ry="34" fill="${R.turuncu}"/>
    <path d="M96 118 Q118 112 132 128 Q114 144 92 134 Z" fill="#E07F22"/>
    <path d="M54 50 Q56 32 66 42 Q68 26 80 38 Q88 26 92 46 Z" fill="${R.kirmizi}"/>
    <circle cx="74" cy="72" r="24" fill="${R.turuncu}"/>
    <path d="M52 68 L34 74 L52 82 Z" fill="${R.sari}"/>
    <path d="M56 84 Q50 102 62 102 Q66 92 64 84 Z" fill="${R.kirmizi}"/>
    ${goz(70, 66, 5)}`,

  izgara: () => `
    <path d="M78 54 q-8 -10 0 -20 q8 -10 0 -20 M104 54 q-8 -10 0 -20 q8 -10 0 -20 M130 54 q-8 -10 0 -20 q8 -10 0 -20" fill="none" stroke="${R.gri}" stroke-width="5"/>
    <rect x="56" y="70" width="44" height="18" rx="9" fill="#B5552B"/>
    <rect x="104" y="70" width="44" height="18" rx="9" fill="#B5552B"/>
    <path d="M66 74 l6 10 M80 74 l6 10 M114 74 l6 10 M128 74 l6 10" fill="none" stroke="${R.koyuKahve}" stroke-width="3"/>
    <path d="M70 140 L54 184 M130 140 L146 184 M100 150 L100 184" fill="none" stroke-width="6"/>
    <path d="M40 94 L160 94 Q160 152 100 152 Q40 152 40 94 Z" fill="${R.kirmizi}"/>
    <path d="M34 92 L166 92" fill="none" stroke-width="7"/>
    <path d="M60 110 Q70 126 86 132" fill="none" stroke="#fff" stroke-width="5" opacity=".6"/>`,

  inek: () => `
    <path d="M70 58 Q54 36 70 22 Q72 40 82 52 Z" fill="${R.krem}"/>
    <path d="M130 58 Q146 36 130 22 Q128 40 118 52 Z" fill="${R.krem}"/>
    <ellipse cx="44" cy="80" rx="24" ry="12" fill="#fff" transform="rotate(-18 44 80)"/>
    <ellipse cx="156" cy="80" rx="24" ry="12" fill="#fff" transform="rotate(18 156 80)"/>
    <ellipse cx="46" cy="81" rx="13" ry="5" fill="${R.pembe}" stroke="none" transform="rotate(-18 46 81)"/>
    <ellipse cx="154" cy="81" rx="13" ry="5" fill="${R.pembe}" stroke="none" transform="rotate(18 154 81)"/>
    <path d="M62 50 Q100 36 138 50 Q154 96 140 132 L60 132 Q46 96 62 50 Z" fill="#fff"/>
    <path d="M66 56 Q84 50 92 64 Q90 86 70 84 Q60 72 66 56 Z" fill="${R.murekkep}" stroke="none"/>
    <path d="M128 92 Q142 88 142 104 Q134 116 124 108 Q120 98 128 92 Z" fill="${R.murekkep}" stroke="none"/>
    ${goz(80, 96)}${goz(120, 96)}
    <ellipse cx="100" cy="142" rx="52" ry="32" fill="${R.pembe}"/>
    <ellipse cx="82" cy="140" rx="7" ry="10" fill="${R.koyuPembe}" stroke="none"/>
    <ellipse cx="118" cy="140" rx="7" ry="10" fill="${R.koyuPembe}" stroke="none"/>
    <path d="M90 160 Q100 166 110 160" fill="none"/>`,

  jole: () => `
    <ellipse cx="100" cy="160" rx="74" ry="16" fill="#fff"/>
    <path d="M56 156 Q50 112 64 74 Q100 60 136 74 Q150 112 144 156 Q100 168 56 156 Z" fill="#7BC96F"/>
    <path d="M64 74 Q100 88 136 74" fill="none"/>
    <path d="M80 82 Q76 118 80 156 M120 82 Q124 118 120 156" fill="none" stroke="#4E9A47" stroke-width="4"/>
    <path d="M68 90 Q64 116 68 140" fill="none" stroke="#fff" stroke-width="6" opacity=".7"/>
    <circle cx="100" cy="62" r="12" fill="${R.kirmizi}"/>
    <path d="M102 52 Q106 40 116 36" fill="none" stroke-width="4"/>
    <path d="M40 120 q-8 0 -10 -8 M160 120 q8 0 10 -8 M36 100 q-6 -2 -6 -8 M164 100 q6 -2 6 -8" fill="none" stroke="${R.koyuGri}" stroke-width="4"/>`,

  kedi: () => `
    <path d="M138 164 Q182 156 166 112" fill="none" stroke="${R.murekkep}" stroke-width="20"/>
    <path d="M138 164 Q182 156 166 112" fill="none" stroke="${R.turuncu}" stroke-width="10"/>
    <ellipse cx="100" cy="144" rx="46" ry="40" fill="${R.turuncu}"/>
    <ellipse cx="100" cy="152" rx="22" ry="24" fill="${R.krem}" stroke="none"/>
    <path d="M64 70 L66 28 L96 52 Z" fill="${R.turuncu}"/>
    <path d="M136 70 L134 28 L104 52 Z" fill="${R.turuncu}"/>
    <path d="M70 58 L72 40 L86 52 Z M130 58 L128 40 L114 52 Z" fill="${R.pembe}" stroke="none"/>
    <circle cx="100" cy="86" r="40" fill="${R.turuncu}"/>
    <path d="M100 48 l0 12 M88 50 l3 11 M112 50 l-3 11" fill="none" stroke="#C9661A" stroke-width="4"/>
    <ellipse cx="84" cy="84" rx="5.5" ry="8" fill="${R.murekkep}" stroke="none"/><ellipse cx="116" cy="84" rx="5.5" ry="8" fill="${R.murekkep}" stroke="none"/>
    <circle cx="86" cy="81" r="2" fill="#fff" stroke="none"/><circle cx="118" cy="81" r="2" fill="#fff" stroke="none"/>
    <path d="M94 98 L106 98 L100 105 Z" fill="${R.koyuPembe}" stroke-width="3"/>
    <path d="M100 105 q-6 9 -13 4 M100 105 q6 9 13 4" fill="none" stroke-width="3.5"/>
    <path d="M72 100 L46 96 M72 106 L48 110 M128 100 L154 96 M128 106 L152 110" fill="none" stroke-width="3"/>
    ${yanak(74, 100)}${yanak(126, 100)}`,

  limon: () => `
    <path d="M22 92 Q34 46 92 44 Q150 46 162 92 Q150 138 92 140 Q34 138 22 92 Z" fill="${R.sari}"/>
    <path d="M92 44 Q96 30 106 24" fill="none" stroke="${R.koyuKahve}" stroke-width="5"/>
    <path d="M100 34 Q120 16 142 26 Q124 46 100 34 Z" fill="${R.yesil}"/>
    <ellipse cx="60" cy="78" rx="7" ry="14" fill="#fff" stroke="none" opacity=".6" transform="rotate(60 60 78)"/>
    <circle cx="146" cy="148" r="34" fill="${R.sari}"/>
    <circle cx="146" cy="148" r="25" fill="#FFF3B0" stroke-width="3"/>
    <path d="M146 148 L146 123 M146 148 L170 141 M146 148 L161 168 M146 148 L131 168 M146 148 L122 141" fill="none" stroke="${R.koyuSari}" stroke-width="3"/>`,

  muz: () => `
    <path d="M44 66 Q50 160 162 152 Q172 150 170 140 Q78 134 64 62 Z" fill="${R.sari}"/>
    <path d="M60 84 Q78 134 150 144" fill="none" stroke="${R.koyuSari}" stroke-width="4"/>
    <path d="M42 68 L38 46 L54 42 L64 64 Z" fill="${R.kahve}"/>
    <path d="M162 152 L172 156 L174 146 L170 140 Z" fill="${R.koyuKahve}"/>`,

  nar: () => `
    <path d="M82 62 L76 38 L92 50 L100 32 L108 50 L124 38 L118 62 Z" fill="#A82632"/>
    <circle cx="96" cy="112" r="58" fill="#C8323C"/>
    <ellipse cx="68" cy="92" rx="8" ry="16" fill="#fff" stroke="none" opacity=".5" transform="rotate(30 68 92)"/>
    <g fill="#F06A80"><ellipse cx="150" cy="168" rx="8" ry="10" transform="rotate(-20 150 168)"/><ellipse cx="170" cy="158" rx="8" ry="10" transform="rotate(20 170 158)"/><ellipse cx="166" cy="180" rx="8" ry="10"/></g>
    <g fill="#fff" stroke="none"><circle cx="148" cy="164" r="2.5"/><circle cx="168" cy="154" r="2.5"/><circle cx="164" cy="176" r="2.5"/></g>`,

  otobus: () => `
    <rect x="22" y="56" width="158" height="94" rx="18" fill="${R.turuncu}"/>
    <g fill="${R.acikMavi}"><rect x="36" y="70" width="28" height="30" rx="5"/><rect x="72" y="70" width="28" height="30" rx="5"/><rect x="108" y="70" width="28" height="30" rx="5"/><rect x="144" y="70" width="24" height="30" rx="5"/></g>
    <path d="M22 116 L180 116" fill="none" stroke="#fff" stroke-width="8"/>
    <circle cx="168" cy="132" r="6" fill="${R.sari}"/>
    <circle cx="60" cy="152" r="17" fill="${R.murekkep}"/><circle cx="60" cy="152" r="7" fill="${R.gri}"/>
    <circle cx="144" cy="152" r="17" fill="${R.murekkep}"/><circle cx="144" cy="152" r="7" fill="${R.gri}"/>`,

  ordek: () => `
    <path d="M14 168 q16 -12 32 0 t32 0 t32 0 t32 0 t32 0 t32 0" fill="none" stroke="${R.mavi}" stroke-width="6"/>
    <path d="M44 124 Q46 162 104 162 Q160 162 172 116 L152 126 Q140 108 108 110 Q70 108 44 124 Z" fill="#E9DFD0"/>
    <path d="M98 128 Q126 116 148 130 Q132 148 104 142 Z" fill="${R.koyuGri}"/>
    <path d="M118 128 L132 132" fill="none" stroke="${R.mavi}" stroke-width="6"/>
    <path d="M58 104 Q76 112 92 106" fill="none" stroke="#fff" stroke-width="7"/>
    <circle cx="74" cy="82" r="28" fill="${R.koyuYesil}"/>
    <path d="M50 84 Q30 84 26 94 Q38 102 54 96 Z" fill="${R.sari}"/>
    ${goz(70, 76, 5)}`,

  pasta: () => `
    <ellipse cx="100" cy="172" rx="74" ry="12" fill="#fff"/>
    <rect x="38" y="106" width="124" height="64" rx="10" fill="${R.pembe}"/>
    <path d="M38 118 Q38 106 50 106 L150 106 Q162 106 162 118 L162 124 Q154 136 146 124 Q138 138 130 124 Q120 138 112 124 Q104 138 96 124 Q88 138 80 124 Q72 138 64 124 Q56 136 48 124 Q42 132 38 124 Z" fill="#fff"/>
    <g fill="${R.kirmizi}" stroke="none"><circle cx="64" cy="152" r="5"/><circle cx="100" cy="152" r="5"/><circle cx="136" cy="152" r="5"/></g>
    <rect x="66" y="74" width="12" height="32" rx="3" fill="${R.mavi}"/>
    <rect x="94" y="68" width="12" height="38" rx="3" fill="${R.sari}"/>
    <rect x="122" y="74" width="12" height="32" rx="3" fill="${R.yesil}"/>
    <path d="M72 70 Q62 58 72 46 Q82 58 72 70 Z M100 64 Q90 52 100 40 Q110 52 100 64 Z M128 70 Q118 58 128 46 Q138 58 128 70 Z" fill="${R.turuncu}" stroke-width="4"/>`,

  roket: () => `
    ${parilti(36, 50)}${parilti(166, 70, 0.8)}${parilti(160, 160, 0.7)}
    <path d="M84 134 Q100 188 116 134 Z" fill="${R.turuncu}"/>
    <path d="M92 134 Q100 166 108 134 Z" fill="${R.sari}" stroke="none"/>
    <path d="M70 98 L44 144 L72 134 Z" fill="${R.kirmizi}"/>
    <path d="M130 98 L156 144 L128 134 Z" fill="${R.kirmizi}"/>
    <path d="M100 18 Q138 56 134 124 L66 124 Q62 56 100 18 Z" fill="#fff"/>
    <path d="M100 18 Q120 36 128 64 L72 64 Q80 36 100 18 Z" fill="${R.kirmizi}"/>
    <circle cx="100" cy="92" r="15" fill="${R.acikMavi}" stroke-width="6"/>
    <rect x="80" y="124" width="40" height="12" rx="3" fill="${R.koyuGri}"/>`,

  saat: () => `
    <path d="M70 160 L58 182 M130 160 L142 182" fill="none" stroke-width="7"/>
    <path d="M38 62 A28 28 0 0 1 82 36 Z" fill="${R.kirmizi}"/>
    <path d="M162 62 A28 28 0 0 0 118 36 Z" fill="${R.kirmizi}"/>
    <circle cx="100" cy="110" r="60" fill="${R.kirmizi}"/>
    <circle cx="100" cy="110" r="46" fill="#fff"/>
    <g fill="none" stroke-width="5"><path d="M100 70 v8 M140 110 h-8 M100 150 v-8 M60 110 h8"/></g>
    <path d="M100 110 L100 82 M100 110 L122 120" fill="none" stroke-width="6"/>
    <circle cx="100" cy="110" r="5" fill="${R.murekkep}"/>`,

  semsiye: () => `
    <g fill="${R.acikMavi}"><path d="M30 34 q-5 8 0 12 q5 -4 0 -12 Z"/><path d="M166 26 q-5 8 0 12 q5 -4 0 -12 Z"/><path d="M178 70 q-5 8 0 12 q5 -4 0 -12 Z"/><path d="M20 80 q-5 8 0 12 q5 -4 0 -12 Z"/></g>
    <path d="M100 104 L100 164 Q100 182 84 182 Q70 182 70 168" fill="none" stroke-width="8"/>
    <path d="M26 104 Q26 38 100 38 Q174 38 174 104 Q160 90 145 104 Q130 90 115 104 Q100 90 85 104 Q70 90 55 104 Q40 90 26 104 Z" fill="${R.mavi}"/>
    <path d="M100 38 Q58 52 55 104 Z M100 38 Q142 52 145 104 Z" fill="${R.sari}" stroke="none"/>
    <path d="M26 104 Q26 38 100 38 Q174 38 174 104 Q160 90 145 104 Q130 90 115 104 Q100 90 85 104 Q70 90 55 104 Q40 90 26 104 Z" fill="none"/>
    <path d="M100 38 Q58 52 55 104 M100 38 Q142 52 145 104 M100 38 L100 98" fill="none" stroke-width="4"/>
    <path d="M100 38 L100 26" fill="none" stroke-width="6"/>`,

  top: () => `
    <path d="M100 48 A60 60 0 0 0 100 168 C70 146 70 70 100 48 Z" fill="${R.kirmizi}"/>
    <path d="M100 48 A60 60 0 0 1 100 168 C130 146 130 70 100 48 Z" fill="${R.mavi}"/>
    <path d="M100 48 C70 70 70 146 100 168 C130 146 130 70 100 48 Z" fill="${R.sari}"/>
    <circle cx="100" cy="108" r="60" fill="none"/>
    <ellipse cx="70" cy="82" rx="7" ry="13" fill="#fff" stroke="none" opacity=".6" transform="rotate(40 70 82)"/>
    <ellipse cx="100" cy="184" rx="44" ry="6" fill="${R.gri}" stroke="none" opacity=".5"/>`,

  ucak: () => `
    <path d="M150 52 q8 -14 22 -8 q12 -6 18 6 q8 2 6 10 l-46 0 Z" fill="#fff" stroke="${R.gri}" stroke-width="4"/>
    <path d="M14 150 q6 -12 18 -8 q10 -10 22 0 q8 0 8 8 Z" fill="#fff" stroke="${R.gri}" stroke-width="4"/>
    <path d="M96 94 L114 94 L100 64 L86 64 Z" fill="${R.koyuGri}"/>
    <path d="M44 96 L30 56 L56 56 L76 96 Z" fill="${R.kirmizi}"/>
    <path d="M30 108 Q30 92 52 92 L150 92 Q182 94 182 108 Q182 122 150 124 L52 124 Q30 124 30 108 Z" fill="#fff"/>
    <path d="M36 114 L178 114" fill="none" stroke="${R.mavi}" stroke-width="6"/>
    <g fill="${R.acikMavi}" stroke-width="3"><circle cx="70" cy="104" r="5"/><circle cx="88" cy="104" r="5"/><circle cx="106" cy="104" r="5"/><circle cx="124" cy="104" r="5"/></g>
    <path d="M150 98 L166 98 Q174 100 176 106 L152 106 Z" fill="${R.acikMavi}" stroke-width="3"/>
    <path d="M88 112 L124 112 L96 160 L78 160 Z" fill="${R.koyuGri}"/>`,

  uzum: () => `
    <path d="M100 52 Q100 34 112 24" fill="none" stroke="${R.koyuKahve}" stroke-width="6"/>
    <path d="M104 40 Q126 20 150 32 Q128 54 104 40 Z" fill="${R.yesil}"/>
    <g fill="${R.mor}">
      <circle cx="100" cy="150" r="17"/>
      <circle cx="84" cy="124" r="17"/><circle cx="116" cy="124" r="17"/>
      <circle cx="68" cy="98" r="17"/><circle cx="100" cy="98" r="17"/><circle cx="132" cy="98" r="17"/>
      <circle cx="54" cy="72" r="17"/><circle cx="86" cy="70" r="17"/><circle cx="118" cy="70" r="17"/><circle cx="148" cy="72" r="17"/>
    </g>
    <g fill="#fff" stroke="none" opacity=".7"><circle cx="94" cy="144" r="3.5"/><circle cx="78" cy="118" r="3.5"/><circle cx="110" cy="118" r="3.5"/><circle cx="62" cy="92" r="3.5"/><circle cx="94" cy="92" r="3.5"/><circle cx="126" cy="92" r="3.5"/><circle cx="48" cy="66" r="3.5"/><circle cx="80" cy="64" r="3.5"/><circle cx="112" cy="64" r="3.5"/><circle cx="142" cy="66" r="3.5"/></g>`,

  vazo: () => {
    const lale = (x, y, renk) => `<path d="M${x - 15} ${y} Q${x - 15} ${y + 24} ${x} ${y + 24} Q${x + 15} ${y + 24} ${x + 15} ${y} L${x + 7} ${y + 9} L${x} ${y - 4} L${x - 7} ${y + 9} Z" fill="${renk}"/>`;
    return `
    <path d="M78 104 Q74 80 70 70 M100 104 L100 60 M122 104 Q126 82 132 72" fill="none" stroke="${R.koyuYesil}" stroke-width="5"/>
    <path d="M100 96 Q80 84 82 70 Q96 76 100 96 Z M100 92 Q118 80 120 66 Q104 72 100 92 Z" fill="${R.yesil}" stroke-width="4"/>
    ${lale(70, 46, R.kirmizi)}${lale(100, 36, R.sari)}${lale(132, 48, R.pembe)}
    <path d="M78 116 Q58 142 70 178 L130 178 Q142 142 122 116 L118 102 L82 102 Z" fill="${R.mavi}"/>
    <path d="M70 140 Q100 150 130 140" fill="none" stroke="#fff" stroke-width="6"/>
    <g fill="#fff" stroke="none"><circle cx="86" cy="160" r="4"/><circle cx="100" cy="164" r="4"/><circle cx="114" cy="160" r="4"/></g>`;
  },

  yildiz: () => `
    ${parilti(34, 40, 0.9)}${parilti(168, 46, 0.7)}${parilti(162, 168, 0.8)}${parilti(32, 160, 0.6)}
    <path d="${yildizYolu(100, 108, 76, 34)}" fill="${R.sari}" stroke-width="6"/>
    ${goz(86, 104)}${goz(114, 104)}${yanak(76, 120)}${yanak(124, 120)}
    <path d="M90 124 Q100 134 110 124" fill="none"/>`,

  zurafa: () => `
    <path d="M160 120 Q176 130 172 150" fill="none"/>
    <g fill="${R.sari}"><rect x="92" y="130" width="12" height="54" rx="5"/><rect x="108" y="134" width="12" height="50" rx="5"/><rect x="140" y="134" width="12" height="50" rx="5"/><rect x="154" y="130" width="12" height="54" rx="5"/></g>
    <ellipse cx="130" cy="128" rx="44" ry="26" fill="${R.sari}"/>
    <path d="M90 126 L62 52 L84 46 L116 118 Z" fill="${R.sari}"/>
    <path d="M64 34 L62 18 M78 32 L80 16" fill="none" stroke-width="5"/>
    <circle cx="62" cy="16" r="5" fill="${R.kahve}"/><circle cx="80" cy="14" r="5" fill="${R.kahve}"/>
    <ellipse cx="88" cy="40" rx="11" ry="6" fill="${R.sari}" transform="rotate(-20 88 40)"/>
    <ellipse cx="62" cy="46" rx="26" ry="17" fill="${R.sari}" transform="rotate(-18 62 46)"/>
    <ellipse cx="42" cy="54" rx="13" ry="10" fill="#E8A94E" stroke="none" transform="rotate(-18 42 54)"/>
    <g fill="${R.kahve}" stroke="none">
      <ellipse cx="116" cy="120" rx="9" ry="7"/><ellipse cx="140" cy="116" rx="8" ry="6"/><ellipse cx="128" cy="138" rx="8" ry="6"/><ellipse cx="156" cy="132" rx="7" ry="6"/>
      <ellipse cx="94" cy="104" rx="6" ry="5"/><ellipse cx="82" cy="82" rx="5" ry="5"/><ellipse cx="96" cy="76" rx="4" ry="4"/><ellipse cx="74" cy="64" rx="4" ry="4"/>
    </g>
    ${goz(66, 40, 5)}
    <path d="M36 56 q4 2 8 0" fill="none" stroke-width="3"/>`,
};

function resim(ad) {
  const f = RESIMLER[ad];
  if (!f) throw new Error('Resim yok: ' + ad);
  return `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" role="img"><g stroke="${R.murekkep}" stroke-width="5" stroke-linejoin="round" stroke-linecap="round">${f()}</g></svg>`;
}

module.exports = { resim, RESIMLER, RENK: R };
