<script setup lang="ts">
import { useEngineStore } from "../stores/engine";
const store = useEngineStore();
</script>

<template>
  <section class="about">
    <h1>Dastur haqida</h1>
    <div class="panel">
      <h2>ArabMorph AI — desktop (sinov versiyasi)</h2>
      <p v-if="store.version">
        Dvigatel v{{ store.version.engine }} · {{ store.version.rules }} qoida · {{ store.version.lexicon_entries }} lug'at yozuvi
        ({{ store.version.lexicon_sources.join(", ") }})
      </p>
      <p>
        Barcha hisob-kitob shu kompyuterda bajariladi. Dastur internetga ulanmaydi, tashqi sun'iy intellekt
        xizmatidan foydalanmaydi va hech qanday API kalitini talab qilmaydi.
      </p>
    </div>
    <div class="panel">
      <h2>Hozir nima bor</h2>
      <ul>
        <li>Birlik i'robi: munsarif, mamnu' min as-sarf, manqus, maqsur.</li>
        <li>Ikkilik: barcha kelishiklar, ال va izofa holatlari, maqsur/manqus/mamdud va hamza imlosi.</li>
        <li>Ko'plik: muzakkar solim, muannas solim, siniq ko'plik (faqat lug'atdan).</li>
        <li>Kelishikni oldingi so'zdan aniqlash: harflar jarr, إنّ va كان guruhlari.</li>
      </ul>
    </div>
    <div class="panel">
      <h2>Cheklovlar</h2>
      <ul>
        <li>Qoidalar va lug'at yozuvlari hali arab tili mutaxassisi tomonidan tekshirilmagan.</li>
        <li>Lug'atda 41 ta so'z bor; lug'atda yo'q so'zlar uchun siniq ko'plik yasalmaydi.</li>
        <li>Kontekst faqat bitta oldingi so'z bo'yicha; to'liq gap tahlili hali yo'q.</li>
        <li>Qo'shimcha harflar (بالكتاب، كتابه) va "besh ism" (أب، أخ…) qo'llab-quvvatlanmaydi.</li>
        <li>Ishonch foizlari qo'lda belgilangan; ular ehtimollik emas, o'qilishlarni tartiblash uchun.</li>
        <li>Dvigatel izohlari hozircha ingliz va arab tillarida.</li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.about { display: flex; flex-direction: column; gap: 12px; max-width: 760px; }
.about h1 { margin-bottom: 4px; }
ul { margin: 0; padding-inline-start: 20px; }
</style>
