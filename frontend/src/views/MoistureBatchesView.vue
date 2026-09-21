<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import api from '../api'

const batches = ref([])
const greenhouses = ref([])
const zones = ref([])
const readings = ref([])
const reconcileRows = ref([])
const error = ref('')
const pointError = ref('')
const filterGreenhouseId = ref('')
const currentBatch = ref(null)

function localInputValue(d = new Date()) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function localDateValue(d = new Date()) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

const batchForm = reactive({
  greenhouseId: '',
  batchNo: '',
  openDate: localDateValue(),
})

const pointForm = reactive({
  zoneId: '',
  moisturePct: 50,
  sampledAt: localInputValue(),
})

const currentZones = computed(() => {
  if (!currentBatch.value) return []
  return zones.value.filter((z) => z.greenhouseId === currentBatch.value.greenhouseId)
})

function fmtTime(v) {
  return v ? new Date(v).toLocaleString() : '—'
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
    if (currentBatch.value) {
      currentBatch.value = batches.value.find((b) => b.id === currentBatch.value.id) || null
    }
  } catch {
    error.value = '加载抽检批次失败'
  }
}

async function loadReconcile() {
  try {
    const { data } = await api.get('/moisture-batches/reconcile/')
    reconcileRows.value = data.results || data
  } catch {
    reconcileRows.value = []
  }
}

async function loadReadings() {
  if (!currentBatch.value) {
    readings.value = []
    return
  }
  const { data } = await api.get('/moisture-readings/', {
    params: { batchId: currentBatch.value.id },
  })
  readings.value = data.results || data
}

async function createBatch() {
  error.value = ''
  if (!batchForm.batchNo.trim()) {
    error.value = '请填写批次号'
    return
  }
  try {
    await api.post('/moisture-batches/', {
      greenhouseId: Number(batchForm.greenhouseId),
      batchNo: batchForm.batchNo.trim(),
      openDate: batchForm.openDate,
    })
    batchForm.batchNo = ''
    batchForm.openDate = localDateValue()
    await loadBatches()
    await loadReconcile()
  } catch (e) {
    error.value = JSON.stringify(e.response?.data || '开批失败')
  }
}

async function selectBatch(row) {
  currentBatch.value = row
  pointForm.zoneId = currentZones.value[0]?.id || ''
  pointForm.moisturePct = 50
  pointForm.sampledAt = localInputValue()
  pointError.value = ''
  await loadReadings()
}

async function addPoint() {
  pointError.value = ''
  if (!currentBatch.value) return
  const pct = Number(pointForm.moisturePct)
  if (!Number.isInteger(pct) || pct < 5 || pct > 95) {
    pointError.value = '含水百分数须为 5～95 的整数'
    return
  }
  try {
    await api.post('/moisture-readings/', {
      batchId: currentBatch.value.id,
      zoneId: Number(pointForm.zoneId),
      moisturePct: pct,
      sampledAt: new Date(pointForm.sampledAt).toISOString(),
    })
    pointForm.sampledAt = localInputValue()
    await loadReadings()
    await loadBatches()
    await loadReconcile()
  } catch (e) {
    pointError.value = JSON.stringify(e.response?.data || '加点失败')
  }
}

async function removePoint(id) {
  if (!confirm('确认删除该测点？')) return
  await api.delete(`/moisture-readings/${id}/`)
  await loadReadings()
  await loadBatches()
  await loadReconcile()
}

async function seal(row) {
  error.value = ''
  try {
    await api.post(`/moisture-batches/${row.id}/seal/`)
    await loadBatches()
  } catch (e) {
    error.value = e.response?.data?.detail || JSON.stringify(e.response?.data || '封批失败')
  }
}

async function removeBatch(id) {
  if (!confirm('确认删除该批次及其全部测点？')) return
  await api.delete(`/moisture-batches/${id}/`)
  if (currentBatch.value?.id === id) {
    currentBatch.value = null
    readings.value = []
  }
  await loadBatches()
  await loadReconcile()
}

onMounted(async () => {
  await loadGreenhouses()
  await loadZones()
  await loadBatches()
  await loadReconcile()
})
</script>

<template>
  <div>
    <div class="page-head">
      <div>
        <h1>含水抽检</h1>
        <p>土壤含水抽检批次：批次挂温室、测点挂分区；封批需箱内至少两点，封后禁止加点</p>
      </div>
      <div class="actions">
        <select v-model="filterGreenhouseId" @change="loadBatches">
          <option value="">全部温室</option>
          <option v-for="g in greenhouses" :key="g.id" :value="g.id">{{ g.name }}</option>
        </select>
      </div>
    </div>

    <div class="panel">
      <h3 style="margin-top:0">新建批次</h3>
      <div class="form-grid">
        <label>
          所属温室
          <select v-model="batchForm.greenhouseId">
            <option v-for="g in greenhouses" :key="g.id" :value="g.id">{{ g.name }}</option>
          </select>
        </label>
        <label>批次号<input v-model="batchForm.batchNo" placeholder="同温室内唯一，跨温室可重复" /></label>
        <label>开批日（东八区自然日）<input v-model="batchForm.openDate" type="date" /></label>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
      <div class="actions" style="margin-top:12px">
        <button class="btn" @click="createBatch">开批</button>
      </div>
    </div>

    <div class="panel">
      <h3 style="margin-top:0">批次列表</h3>
      <table>
        <thead>
          <tr>
            <th>批次号</th>
            <th>温室</th>
            <th>开批日</th>
            <th>测点数</th>
            <th>封批时刻</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in batches" :key="row.id">
            <td>{{ row.batchNo }}</td>
            <td>{{ row.greenhouseName }}</td>
            <td>{{ row.openDate }}</td>
            <td>{{ row.readingCount }}</td>
            <td>{{ fmtTime(row.sealedAt) }}</td>
            <td>
              <span class="badge" :class="row.sealedAt ? 'done' : 'running'">
                {{ row.sealedAt ? '已封' : '未封' }}
              </span>
            </td>
            <td class="actions">
              <button class="btn ghost" @click="selectBatch(row)">测点</button>
              <button v-if="!row.sealedAt" class="btn" @click="seal(row)">封批</button>
              <button class="btn danger" @click="removeBatch(row.id)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="currentBatch" class="panel">
      <h3 style="margin-top:0">
        测点明细 · {{ currentBatch.greenhouseName }} / {{ currentBatch.batchNo }}
        <span class="badge" :class="currentBatch.sealedAt ? 'done' : 'running'">
          {{ currentBatch.sealedAt ? '已封' : '未封' }}
        </span>
      </h3>
      <template v-if="!currentBatch.sealedAt">
        <div class="form-grid">
          <label>
            分区（限本温室）
            <select v-model="pointForm.zoneId">
              <option v-for="z in currentZones" :key="z.id" :value="z.id">{{ z.zoneCode }}</option>
            </select>
          </label>
          <label>含水 %<input v-model.number="pointForm.moisturePct" type="number" min="5" max="95" step="1" /></label>
          <label>采样时刻<input v-model="pointForm.sampledAt" type="datetime-local" /></label>
        </div>
        <p v-if="pointError" class="error">{{ pointError }}</p>
        <div class="actions" style="margin-top:12px">
          <button class="btn" @click="addPoint">加点</button>
        </div>
      </template>
      <p v-else class="hint">批次已封，禁止加点。</p>
      <table>
        <thead>
          <tr>
            <th>分区</th>
            <th>含水 %</th>
            <th>采样时刻</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in readings" :key="r.id">
            <td>{{ r.zoneCode }}</td>
            <td>{{ r.moisturePct }}</td>
            <td>{{ fmtTime(r.sampledAt) }}</td>
            <td class="actions">
              <button class="btn danger" @click="removePoint(r.id)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="panel">
      <h3 style="margin-top:0">对账 · 按温室</h3>
      <table>
        <thead>
          <tr>
            <th>温室</th>
            <th>批次数</th>
            <th>点数</th>
            <th>明细批次</th>
            <th>明细点数</th>
            <th>批次差</th>
            <th>点数差</th>
            <th>结论</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in reconcileRows" :key="row.greenhouseId">
            <td>{{ row.greenhouseName }}</td>
            <td>{{ row.batchCount }}</td>
            <td>{{ row.pointCount }}</td>
            <td>{{ row.detailBatchCount }}</td>
            <td>{{ row.detailPointCount }}</td>
            <td>{{ row.batchDiff }}</td>
            <td>{{ row.pointDiff }}</td>
            <td>
              <span class="badge" :class="row.batchDiff === 0 && row.pointDiff === 0 ? 'done' : 'skipped'">
                {{ row.batchDiff === 0 && row.pointDiff === 0 ? '平账' : '有差' }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
