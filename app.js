// ─── Utilities ───
const WEEKDAYS = ['Неділя','Понеділок','Вівторок','Середа','Четвер','П\'ятниця','Субота'];

function formatDate(dtStr) {
  const d = new Date(dtStr + 'T00:00:00');
  const day = String(d.getDate()).padStart(2, '0');
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const year = d.getFullYear();
  const wk = WEEKDAYS[d.getDay()];
  return `${wk}, ${day}.${month}.${year}`;
}

// ─── Build unique lists ───
function getUniqueTeachers(data) {
  // Step 1: collect unique tids with their surname and subjects
  const tidMap = new Map(); // tid -> { fam, subjects: Set }
  data.forEach(r => {
    if (!tidMap.has(r.tid)) {
      tidMap.set(r.tid, { fam: r.fam, subjects: new Set() });
    }
    tidMap.get(r.tid).subjects.add(r.lesson);
  });

  // Step 2: detect surnames that have multiple tids (different people)
  const famCount = new Map(); // fam -> [tid, tid, ...]
  tidMap.forEach((info, tid) => {
    if (!famCount.has(info.fam)) famCount.set(info.fam, []);
    famCount.get(info.fam).push(tid);
  });

  // Step 3: build list, add disambiguation for duplicates
  const result = [];
  tidMap.forEach((info, tid) => {
    const isDuplicate = famCount.get(info.fam).length > 1;
    let label = info.fam;
    if (isDuplicate) {
      // Take first 2 subjects as disambiguation hint
      const subjs = [...info.subjects].slice(0, 2).join(', ');
      label = `${info.fam} (${subjs})`;
    }
    result.push({ fam: label, tid: tid });
  });

  return result.sort((a, b) => a.fam.localeCompare(b.fam, 'uk'));
}

function getUniqueGroups(data) {
  const map = new Map();
  data.forEach(r => {
    if (!map.has(r.gid)) {
      map.set(r.gid, r.gname);
    }
  });
  return Array.from(map.entries())
    .map(([gid, gname]) => ({ gid, gname }))
    .sort((a, b) => a.gname.localeCompare(b.gname, 'uk'));
}

// ─── Group by date ───
function groupByDate(records) {
  const days = new Map();
  records.forEach(r => {
    if (!days.has(r.dt)) days.set(r.dt, []);
    days.get(r.dt).push(r);
  });
  // Sort dates
  const sorted = new Map([...days.entries()].sort((a, b) => a[0].localeCompare(b[0])));
  // Sort pairs within each day
  sorted.forEach((pairs, dt) => {
    pairs.sort((a, b) => a.pair - b.pair);
  });
  return sorted;
}

// ─── Teacher schedule (merge groups per pair) ───
function buildTeacherSchedule(data, tids) {
  const filtered = data.filter(r => tids.includes(r.tid));
  const byDate = groupByDate(filtered);
  const result = new Map();

  byDate.forEach((records, dt) => {
    const merged = [];
    const pairMap = new Map();

    records.forEach(rec => {
      if (!pairMap.has(rec.pair)) {
        pairMap.set(rec.pair, []);
      }
      pairMap.get(rec.pair).push(rec);
    });

    pairMap.forEach((items, pairNum) => {
      // Group by lesson within the same pair
      const lessonMap = new Map();
      items.forEach(item => {
        if (!lessonMap.has(item.lesson)) lessonMap.set(item.lesson, []);
        lessonMap.get(item.lesson).push(item.gname);
      });

      const groupStrs = [];
      const lessonStrs = [];
      
      lessonMap.forEach((groups, lesson) => {
        groupStrs.push(groups.join(', '));
        lessonStrs.push(lesson);
      });

      const separator = '<div style="height:1px; background:var(--border-glass); margin: 6px 0;"></div>';
      
      merged.push({
        pair: pairNum,
        groups: groupStrs.join(separator),
        lesson: lessonStrs.join(separator)
      });
    });

    merged.sort((a, b) => a.pair - b.pair);
    result.set(dt, merged);
  });

  return result;
}

// ─── Group schedule (merge half-pairs) ───
function buildGroupSchedule(data, gid) {
  const filtered = data.filter(r => r.gid === gid);
  const byDate = groupByDate(filtered);
  const result = new Map();

  byDate.forEach((records, dt) => {
    const merged = [];
    const pairMap = new Map();

    records.forEach(rec => {
      if (!pairMap.has(rec.pair)) {
        pairMap.set(rec.pair, []);
      }
      pairMap.get(rec.pair).push(rec);
    });

    pairMap.forEach((items, pairNum) => {
      const famStrs = items.map(item => item.fam);
      const lessonStrs = items.map(item => item.lesson);
      const separator = '<div style="height:1px; background:var(--border-glass); margin: 6px 0;"></div>';

      merged.push({
        pair: pairNum,
        fam: famStrs.join(separator),
        lesson: lessonStrs.join(separator)
      });
    });

    merged.sort((a, b) => a.pair - b.pair);
    result.set(dt, merged);
  });

  return result;
}

// ─── Render HTML ───
function renderTeacherTable(schedule) {
  if (schedule.size === 0) return renderEmpty();
  let html = '';
  schedule.forEach((pairs, dt) => {
    html += `<div class="day-card">
      <div class="day-card__header"><span class="day-icon"><i class="fa-regular fa-calendar-days"></i></span> ${formatDate(dt)}</div>
      <table class="schedule-table">
        <thead><tr><th class="col-pair">Пара</th><th class="col-middle">Групи</th><th class="col-last">Дисципліна</th></tr></thead>
        <tbody>`;
    pairs.forEach(p => {
      html += `<tr>
        <td><span class="pair-number">${p.pair}</span></td>
        <td class="cell-groups">${p.groups}</td>
        <td class="cell-lesson">${p.lesson}</td>
      </tr>`;
    });
    html += `</tbody></table></div>`;
  });
  return html;
}

function renderGroupTable(schedule) {
  if (schedule.size === 0) return renderEmpty();
  let html = '';
  schedule.forEach((pairs, dt) => {
    html += `<div class="day-card">
      <div class="day-card__header"><span class="day-icon">📅</span> ${formatDate(dt)}</div>
      <table class="schedule-table">
        <thead><tr><th class="col-pair">Пара</th><th class="col-middle">Викладач</th><th class="col-last">Дисципліна</th></tr></thead>
        <tbody>`;
    pairs.forEach(p => {
      html += `<tr>
        <td><span class="pair-number">${p.pair}</span></td>
        <td class="cell-teacher">${p.fam}</td>
        <td class="cell-lesson">${p.lesson}</td>
      </tr>`;
    });
    html += `</tbody></table></div>`;
  });
  return html;
}

function renderEmpty() {
  return `<div class="empty-state">
    <div class="empty-state__icon"><i class="fa-regular fa-rectangle-list"></i></div>
    <div class="empty-state__text">Оберіть зі списку, щоб побачити розклад</div>
  </div>`;
}

// ─── Compute date range label ───
function getDateRange(data) {
  if (!data.length) return '';
  const dates = [...new Set(data.map(r => r.dt))].sort();
  return `${formatDate(dates[0])} — ${formatDate(dates[dates.length - 1])}`;
}

// ─── Initialize ───
document.addEventListener('DOMContentLoaded', () => {
  const teachers = getUniqueTeachers(SCHEDULE_DATA);
  const groups = getUniqueGroups(SCHEDULE_DATA);

  // Date range
  const rangeEl = document.getElementById('dateRange');
  if (rangeEl) rangeEl.textContent = getDateRange(SCHEDULE_DATA);

  // DOM Elements
  const teacherOutput = document.getElementById('teacherOutput');
  const teacherTitle = document.getElementById('teacherTitle');
  const groupOutput = document.getElementById('groupOutput');
  const groupTitle = document.getElementById('groupTitle');

  // ─── Setup Custom Selects ───
  setupCustomSelect('groupCustomSelect', 'groupSelectHeader', 'groupSelectDropdown', 'groupSelectValue', 'groupSearchInput', 'groupList', groups, (item) => {
    groupTitle.textContent = item.label;
    const schedule = buildGroupSchedule(SCHEDULE_DATA, parseInt(item.value));
    groupOutput.innerHTML = renderGroupTable(schedule);
  });

  setupCustomSelect('teacherCustomSelect', 'teacherSelectHeader', 'teacherSelectDropdown', 'teacherSelectValue', 'teacherSearchInput', 'teacherList', teachers, (item) => {
    teacherTitle.textContent = item.label;
    const schedule = buildTeacherSchedule(SCHEDULE_DATA, [parseInt(item.value)]);
    teacherOutput.innerHTML = renderTeacherTable(schedule);
  });


  // Tab switching
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.tab;
      tabBtns.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(target).classList.add('active');
    });
  });

  // Init empty states
  teacherOutput.innerHTML = renderEmpty();
  groupOutput.innerHTML = renderEmpty();
});

// ─── Custom Select Logic ───
function setupCustomSelect(containerId, headerId, dropdownId, valueId, searchId, listId, dataItems, onSelect) {
  const container = document.getElementById(containerId);
  const header = document.getElementById(headerId);
  const valueEl = document.getElementById(valueId);
  const searchInput = document.getElementById(searchId);
  const listEl = document.getElementById(listId);

  // Map data to standard format { value, label }
  const items = dataItems.map(d => ({
    value: d.gid || d.tid,
    label: d.gname || d.fam
  }));

  function renderList(filterText = '') {
    listEl.innerHTML = '';
    const filtered = items.filter(i => i.label.toLowerCase().includes(filterText.toLowerCase()));
    
    if (filtered.length === 0) {
      listEl.innerHTML = '<li class="no-results">Нічого не знайдено</li>';
      return;
    }

    filtered.forEach(item => {
      const li = document.createElement('li');
      li.textContent = item.label;
      li.dataset.value = item.value;
      li.addEventListener('click', (e) => {
        e.stopPropagation();
        valueEl.textContent = item.label;
        container.classList.remove('open');
        onSelect(item);
      });
      listEl.appendChild(li);
    });
  }

  // Initial render
  renderList();

  // Toggle dropdown
  header.addEventListener('click', (e) => {
    e.stopPropagation();
    const isOpen = container.classList.contains('open');
    // Close all other selects
    document.querySelectorAll('.custom-select').forEach(el => el.classList.remove('open'));
    if (!isOpen) {
      container.classList.add('open');
      searchInput.value = '';
      renderList();
      searchInput.focus();
    }
  });

  // Search filtering
  searchInput.addEventListener('input', (e) => {
    renderList(e.target.value);
  });

  // Prevent closing when clicking inside dropdown
  document.getElementById(dropdownId).addEventListener('click', (e) => {
    e.stopPropagation();
  });
}

// Close dropdowns when clicking outside
document.addEventListener('click', () => {
  document.querySelectorAll('.custom-select').forEach(el => el.classList.remove('open'));
});
