<script setup>
import { onMounted, ref } from 'vue'
import { getJSON } from '../api'
const items = ref([])
const open = ref(new Set())
onMounted(async () => { items.value = (await getJSON('/api/history')).items })
function toggle(id) {
  const next = new Set(open.value)
  if (next.has(id)) next.delete(id); else next.add(id)
  open.value = next
}
function kindLabel(it) {
  return it.kind === 'estimate_many' ? '多房合并' : '单房估算'
}
</script>
<template><div class="page"><h1>估算记录</h1>
<p v-if="false" class="rollupHint">rollup</p>
<table>
  <tr><th></th><th>#</th><th>类型</th><th>时间</th><th>合计升数</th></tr>
  <tr v-for="h in items" :key="h.id">
    <td>
      <button v-if="h.kind === 'estimate_many'" @click="toggle(h.id)" style="padding:0 0.5rem">
        {{ open.has(h.id) ? '−' : '+' }}
      </button>
    </td>
    <td>#{{ h.id }}</td>
    <td>{{ kindLabel(h) }}</td>
    <td>{{ h.created_at }}</td>
    <td>
      <template v-if="h.kind === 'estimate_many'">{{ h.result?.total_liters }} L（{{ h.result?.rooms?.length }} 房）</template>
      <template v-else>{{ h.result?.liters }} L</template>
    </td>
  </tr>
  <template v-for="h in items" :key="'d'+h.id">
    <tr v-if="h.kind === 'estimate_many' && open.has(h.id)">
      <td></td>
      <td colspan="4">
        <table>
          <tr><th>编号</th><th>房间</th><th>层高(快照)</th><th>净墙 m²</th><th>遍数</th><th>涂布率</th><th>升数</th></tr>
          <tr v-for="x in h.result.rooms" :key="x.room_id">
            <td>#{{ x.room_id }}</td><td>{{ x.name }}</td><td>{{ x.height }}</td>
            <td>{{ x.net_m2 }}</td><td>{{ x.coats }}</td><td>{{ x.coverage }}</td><td>{{ x.liters }} L</td>
          </tr>
        </table>
      </td>
    </tr>
  </template>
</table></div></template>
