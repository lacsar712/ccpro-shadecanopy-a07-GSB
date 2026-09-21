<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import api from '../api'

const batches = ref([])
const zones = ref([])
const greenhouses = ref([])
const reconciliation = ref([])
const error = ref('')
const filterGreenhouseId = ref('')

const expandedId = ref(null)
const expandedSamples = ref([])

function todayLocal() {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function localInputValue(d = new Date()) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const batchForm = reactive({
  greenhouseId: '',
  batchCode: '',
  openedOn: todayLocal(),
})

const sampleForm = reactive({
  zoneId: '',
  moisturePct: 30,
  sampledAt: localInputValue(),
})
const sampleBatchId = ref(null)
const sampleError = ref('')

const zonesByGreenhouse = computed(() => {
  const map = {}
  for (const z of zones.value) {
    (map[z.greenhouseId] ||= []).push(z)
  }
  return map
})

function zonesOfBatch(batch) {
  return zonesByGreenhouse.value[batch.greenhouseId] || []
}

async function loadGreenhouses() {
  const { data } = await api.get('/greenhouses/')
  greenhouses.value = data.results || data
  if (!batchForm.greenhouseId && greenhouses.value.length) {
    batchForm.greenhouseId = greenhouses.value[0].id
  }
}

async function loadZones() {
  const { data } = await api.get('/zones/')
  zones.value = data.results || data
}

async function loadBatches() {
  error.value = ''
  try {
    const params = {}
    if (filterGreenhouseId.value) params.greenhouseId = filterGreenhouseId.value
    const { data } = await api.get('/moisture-batches/', { params })
    batches.value = data.results || data
  } catch {
    error.value = '加载抽检批次失败'
  }
}

async function loadReconciliation() {
  const { data } = await api.get('/moisture-reconciliation/')
  reconciliation.value = data.results || []
}

async function createBatch() {
  error.value = ''
  if (!batchForm.batchCode.trim()) {
    error.value = '批次号不能为空'
    return
  }
  try {
    await api.post('/moisture-batches/', {
      greenhouseId: Number(batchForm.greenhouseId),
      batchCode: batchForm.batchCode.trim(),
      openedOn: batchForm.openedOn,
    })
    batchForm.batchCode = ''
    await loadBatches()
    await loadReconciliation()
  } catch (e) {
    error.value = JSON.stringify(e.response?.data || '开批失败')
  }
}

function openSampleForm(batch) {
  sampleBatchId.value = batch.id
  sampleError.value = ''
  const owned = zonesOfBatch(batch)
  sampleForm.zoneId = owned[0]?.id || ''
  sampleForm.moisturePct = 30
  sampleForm.sampledAt = localInputValue()
}

function cancelSample() {
  sampleBatchId.value = null
}

async function submitSample() {
  sampleError.value = ''
  const pct = Number(sampleForm.moisturePct)
  if (!Number.isInteger(pct) || pct < 5 || pct > 95) {
    sampleError.value = '含水百分数须为 5～95 的整数'
    return
  }
  try {
    await api.post('/moisture-samples/', {
      batchId: sampleBatchId.value,
      zoneId: Number(sampleForm.zoneId),
      moisturePct: pct,
      sampledAt: new Date(sampleForm.sampledAt).toISOString(),
    })
    sampleBatchId.value = null
    await loadBatches()
    if (expandedId.value) await loadSamples(expandedId.value)
    await loadReconciliation()
  } catch (e) {
    sampleError.value = JSON.stringify(e.response?.data || '测点保存失败')
  }
}

async function closeBatch(batch) {
  if (!confirm(`确认封批 ${batch.batchCode}？封批后不能再加点。`)) return
  error.value = ''
  try {
    await api.post(`/moisture-batches/${batch.id}/close/`)
    await loadBatches()
    if (expandedId.value === batch.id) await loadSamples(batch.id)
  } catch (e) {
    if (e.response?.status === 409) {
      error.value = e.response.data?.detail || '箱内测点不足 2 个，不能封批'
    } else {
      error.value = JSON.stringify(e.response?.data || '封批失败')
    }
  }
}

async function loadSamples(batchId) {
  const { data } = await api.get('/moisture-samples/', { params: { batchId } })
  expandedSamples.value = data.results || data
}

async function toggleSamples(batch) {
  if (expandedId.value === batch.id) {
    expandedId.value = null
    expandedSamples.value = []
    return
  }
  expandedId.value = batch.id
  await loadSamples(batch.id)
}

onMounted(async () => {
  await loadGreenhouses()
  await loadZones()
  await loadBatches()
  await loadReconciliation()
})
</script>

<template>
  <div>
    <div class="page-head">
      <div>
        <h1>土壤含水抽检</h1>
        <p>批次挂温室、测点挂分区；含水 ∈ [5, 95] 整数；未封批次同一分区只许一点；封批至少 2 点</p>
      </div>
      <div class="actions">
        <select v-model="filterGreenhouseId" @change="loadBatches">
          <option value="">全部温室</option>
          <option v-for="g in greenhouses" :key="g.id" :value="g.id">{{ g.name }}</option>
        </select>
      </div>
    </div>

    <div class="panel">
      <h3 style="margin-top:0">开批</h3>
      <div class="form-grid">
        <label>
          所属温室
          <select v-model="batchForm.greenhouseId">
            <option v-for="g in greenhouses" :key="g.id" :value="g.id">{{ g.name }}</option>
          </select>
        </label>
        <label>批次号<input v-model="batchForm.batchCode" placeholder="如 SM-20260921-01" /></label>
        <label>开批日（东八区自然日）<input v-model="batchForm.openedOn" type="date" /></label>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
      <div class="actions" style="margin-top:12px">
        <button class="btn" @click="createBatch">开批</button>
      </div>
    </div>

    <div class="panel">
      <table>
        <thead>
          <tr>
            <th>温室</th>
            <th>批次号</th>
            <th>开批日</th>
            <th>点数</th>
            <th>封批时刻</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="b in batches" :key="b.id">
            <tr>
              <td>{{ b.greenhouseName }}</td>
              <td>{{ b.batchCode }}</td>
              <td>{{ b.openedOn }}</td>
              <td>{{ b.sampleCount }}</td>
              <td>
                <span v-if="b.closedAt" class="badge done">{{ new Date(b.closedAt).toLocaleString() }}</span>
                <span v-else class="badge scheduled">未封</span>
              </td>
              <td class="actions">
                <button class="btn ghost" @click="toggleSamples(b)">
                  {{ expandedId === b.id ? '收起明细' : '查看明细' }}
                </button>
                <button
                  v-if="!b.closedAt"
                  class="btn secondary"
                  @click="openSampleForm(b)"
                >
                  加点
                </button>
                <button v-if="!b.closedAt" class="btn" @click="closeBatch(b)">封批</button>
              </td>
            </tr>
            <tr v-if="sampleBatchId === b.id">
              <td colspan="6">
                <div style="padding:8px 4px">
                  <div class="form-grid">
                    <label>
                      分区（限 {{ b.greenhouseName }}）
                      <select v-model="sampleForm.zoneId">
                        <option v-for="z in zonesOfBatch(b)" :key="z.id" :value="z.id">
                          {{ z.zoneCode }}{{ z.cropName ? ' · ' + z.cropName : '' }}
                        </option>
                      </select>
                    </label>
                    <label>含水百分数（5～95 整数）
                      <input v-model.number="sampleForm.moisturePct" type="number" min="5" max="95" step="1" />
                    </label>
                    <label>采样时刻
                      <input v-model="sampleForm.sampledAt" type="datetime-local" />
                    </label>
                  </div>
                  <p v-if="sampleError" class="error">{{ sampleError }}</p>
                  <div class="actions" style="margin-top:10px">
                    <button class="btn" @click="submitSample">提交测点</button>
                    <button class="btn ghost" @click="cancelSample">取消</button>
                  </div>
                </div>
              </td>
            </tr>
            <tr v-if="expandedId === b.id">
              <td colspan="6">
                <table v-if="expandedSamples.length" style="margin:6px 0">
                  <thead>
                    <tr>
                      <th>分区</th>
                      <th>含水 %</th>
                      <th>采样时刻</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="s in expandedSamples" :key="s.id">
                      <td>{{ s.zoneCode }}</td>
                      <td>{{ s.moisturePct }}</td>
                      <td>{{ new Date(s.sampledAt).toLocaleString() }}</td>
                    </tr>
                  </tbody>
                </table>
                <p v-else style="color:var(--muted);margin:6px 2px">该批次暂无测点</p>
              </td>
            </tr>
          </template>
          <tr v-if="!batches.length">
            <td colspan="6" style="color:var(--muted)">暂无批次</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="panel">
      <h3 style="margin-top:0">对账（按温室）</h3>
      <table>
        <thead>
          <tr>
            <th>温室</th>
            <th>批次数</th>
            <th>批次侧点数</th>
            <th>明细计数</th>
            <th>差额</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in reconciliation" :key="r.greenhouseId">
            <td>{{ r.greenhouseName }}</td>
            <td>{{ r.batchCount }}</td>
            <td>{{ r.sampleCount }}</td>
            <td>{{ r.detailSampleCount }}</td>
            <td>
              <span :class="r.diff === 0 ? 'badge done' : 'badge skipped'">{{ r.diff }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
