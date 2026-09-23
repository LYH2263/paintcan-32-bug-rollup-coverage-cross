<script setup>
import { computed, onMounted, ref } from 'vue'
import { getJSON, postJSON } from '../api'

const rooms = ref([])
const picked = ref(new Set())
const coats = ref(null)
const coverage = ref(null)
const out = ref(null)
const err = ref('')

onMounted(async () => { rooms.value = (await getJSON('/api/rooms')).items })

const selectedIds = computed(() => rooms.value.filter(r => picked.value.has(r.id)).map(r => r.id))

function toggle(id) {
  const next = new Set(picked.value)
  if (next.has(id)) next.delete(id); else next.add(id)
  picked.value = next
}

const run = async () => {
  err.value = ''
  out.value = null
  const body = { room_ids: selectedIds.value, persist: true }
  if (coats.value) body.coats = Number(coats.value)
  if (coverage.value) body.coverage = Number(coverage.value)
  try {
    out.value = await postJSON('/api/estimate', body)
  } catch (e) {
    err.value = String(e.message || e)
  }
}
</script>
<template><div class="page"><h1>估漆工作台</h1>
  <table>
    <tr><th></th><th>编号</th><th>房间</th><th>尺寸 长×宽×高 (m)</th></tr>
    <tr v-for="r in rooms" :key="r.id">
      <td><input type="checkbox" :checked="picked.has(r.id)" @change="toggle(r.id)" /></td>
      <td>#{{ r.id }}</td>
      <td>{{ r.name }}</td>
      <td>{{ r.length }}×{{ r.width }}×{{ r.height }}</td>
    </tr>
  </table>
  <p>
    <label>统一遍数（留空用设置） <input v-model.number="coats" type="number" min="1" style="width:5rem" /></label>
    <label>统一涂布率 m²/L（留空用设置） <input v-model.number="coverage" type="number" min="0.1" step="0.1" style="width:6rem" /></label>
  </p>
  <button @click="run">合并估算已选 {{ selectedIds.length }} 间</button>
  <p v-if="err" style="color:#b3261e">请求被拒绝：{{ err }}</p>

  <div v-if="out">
    <h2>分房用量</h2>
    <table>
      <tr><th>编号</th><th>房间</th><th>毛墙 m²</th><th>开洞 m²</th><th>净墙 m²</th><th>遍数</th><th>涂布率</th><th>升数</th></tr>
      <tr v-for="x in out.rooms" :key="x.room_id">
        <td>#{{ x.room_id }}</td><td>{{ x.name }}</td>
        <td>{{ x.gross_m2 }}</td><td>{{ x.openings_m2 }}</td><td>{{ x.net_m2 }}</td>
        <td>{{ x.coats }}</td><td>{{ x.coverage }}</td><td>{{ x.liters }} L</td>
      </tr>
      <tr style="font-weight:700">
        <td colspan="2">合计</td>
        <td>{{ out.total_gross_m2 }}</td><td>{{ out.total_openings_m2 }}</td><td>{{ out.total_net_m2 }}</td>
        <td colspan="2"></td>
        <td>{{ out.total_liters ?? out.rooms?.[0]?.liters }} L</td>
      </tr>
    </table>
    <p v-if="out.run_id">已写入估算记录 #{{ out.run_id }}（分房升数已钉选）</p>
  </div>
</div></template>
