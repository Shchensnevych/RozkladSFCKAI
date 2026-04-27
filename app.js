// ─── Helper Functions ───
function formatDate(dateStr) {
  const d = new Date(dateStr.split(' ')[0]);
  const days = ['Неділя','Понеділок','Вівторок','Середа','Четвер','П’ятниця','Субота'];
  const dd = String(d.getDate()).padStart(2, '0');
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const yyyy = d.getFullYear();
  return `${days[d.getDay()]}, ${dd}.${mm}.${yyyy}`;
}

function formatShortDate(dateObj) {
  const dd = String(dateObj.getDate()).padStart(2, '0');
  const mm = String(dateObj.getMonth() + 1).padStart(2, '0');
  const yyyy = dateObj.getFullYear();
  return `${dd}.${mm}.${yyyy}`;
}

function getUniqueTeachers(data) {
  const map = new Map();
  data.forEach(r => {
    if (!map.has(r.tid)) {
      map.set(r.tid, { tid: r.tid, fam: r.fam });
    }
  });
  
  const teachers = Array.from(map.values());
  const surnameCounts = {};
  teachers.forEach(t => {
    surnameCounts[t.fam] = (surnameCounts[t.fam] || 0) + 1;
  });

  const subjectMap = new Map();
  data.forEach(r => {
    if (!subjectMap.has(r.tid)) subjectMap.set(r.tid, new Set());
    subjectMap.get(r.tid).add(r.lesson);
  });

  teachers.forEach(t => {
    if (surnameCounts[t.fam] > 1) {
      const subjects = Array.from(subjectMap.get(t.tid) || []).slice(0, 2).join(', ');
      t.fam = `${t.fam} (${subjects})`;
    }
  });

  return teachers.sort((a,b) => a.fam.localeCompare(b.fam));
}

function getUniqueGroups(data) {
  const map = new Map();
  data.forEach(r => {
    if (!map.has(r.gid)) map.set(r.gid, { gid: r.gid, gname: r.gname });
  });
  return Array.from(map.values()).sort((a,b) => a.gname.localeCompare(b.gname));
}

// ─── Week Logic ───
function getUniqueWeeks(data) {
  const weeksMap = new Map();
  data.forEach(item => {
    const d = new Date(item.dt.split(' ')[0]);
    let day = d.getDay();
    if (day === 0) day = 7;
    const monday = new Date(d);
    monday.setDate(d.getDate() - day + 1);
    monday.setHours(0,0,0,0);
    
    const key = monday.getTime();
    if (!weeksMap.has(key)) {
      const sunday = new Date(monday);
      sunday.setDate(monday.getDate() + 6);
      weeksMap.set(key, {
        value: key,
        label: `${formatShortDate(monday)} — ${formatShortDate(sunday)}`
      });
    }
  });
  return Array.from(weeksMap.values()).sort((a,b) => a.value - b.value);
}

let CURRENT_WEEK_ID = null;

function filterDataByWeek(data) {
  if (!CURRENT_WEEK_ID) return data;
  return data.filter(item => {
    const d = new Date(item.dt.split(' ')[0]);
    let day = d.getDay();
    if (day === 0) day = 7;
    const monday = new Date(d);
    monday.setDate(d.getDate() - day + 1);
    monday.setHours(0,0,0,0);
    return monday.getTime() === CURRENT_WEEK_ID;
  });
}

// ─── Statistics Logic ───
function renderStats(data, targetId, type) {
  let filtered = data.filter(r => type === 'teacher' ? r.tid === targetId : r.gid === targetId);
  if (filtered.length === 0) return '';

  const subjectPairs = new Map();
  const uniquePairs = new Set();
  
  filtered.forEach(r => {
    // For teachers, concurrent pairs for different groups should count as 1 pair
    // For groups, concurrent pairs are just 1 pair
    const key = `${r.dt}-${r.pair}-${r.lesson}`;
    if (!uniquePairs.has(key)) {
      uniquePairs.add(key);
      subjectPairs.set(r.lesson, (subjectPairs.get(r.lesson) || 0) + 1);
    }
  });

  let totalPairs = 0;
  let badgesHtml = '';
  const sortedSubjects = Array.from(subjectPairs.entries()).sort((a,b) => b[1] - a[1]);
  
  sortedSubjects.forEach(([subject, count]) => {
    totalPairs += count;
    badgesHtml += `<div class="stats-badge" style="cursor: pointer;" onclick="openJournalModal('${type}', ${targetId}, '${subject.replace(/'/g, "\\'")}')" title="Натисніть, щоб переглянути дати">${subject} <span class="stats-badge__count">${count * 2} год</span></div>`;
  });

  return `
    <div class="stats-summary" onclick="this.parentElement.classList.toggle('open')">
      <span><i class="fa-solid fa-chart-pie" style="color: var(--accent-blue); margin-right: 0.5rem;"></i> Всього проведено: <strong>${totalPairs * 2} год</strong></span>
      <i class="fa-solid fa-chevron-down stats-summary__icon"></i>
    </div>
    <div class="stats-details">
      <div class="stats-list">
        ${badgesHtml}
      </div>
    </div>
  `;
}

// ─── Schedule Builders ───
function buildTeacherSchedule(data, tids) {
  const filtered = data.filter(r => tids.includes(r.tid));
  const byDate = {};
  filtered.forEach(r => {
    if (!byDate[r.dt]) byDate[r.dt] = [];
    byDate[r.dt].push(r);
  });

  const schedule = [];
  Object.keys(byDate).sort().forEach(dt => {
    const pairsMap = {};
    byDate[dt].forEach(r => {
      if (!pairsMap[r.pair]) pairsMap[r.pair] = [];
      pairsMap[r.pair].push(r);
    });

    const pairsList = [];
    Object.keys(pairsMap).sort().forEach(p => {
      const records = pairsMap[p];
      const mergedGroups = records.map(r => r.gname).join(', ');
      pairsList.push({
        pair: p,
        gname: mergedGroups,
        lesson: records[0].lesson
      });
    });

    schedule.push({ dt, pairs: pairsList });
  });
  return schedule;
}

function buildGroupSchedule(data, gid) {
  const filtered = data.filter(r => r.gid === gid);
  const byDate = {};
  filtered.forEach(r => {
    if (!byDate[r.dt]) byDate[r.dt] = [];
    byDate[r.dt].push(r);
  });

  const schedule = [];
  Object.keys(byDate).sort().forEach(dt => {
    const pairsMap = {};
    byDate[dt].forEach(r => {
      if (!pairsMap[r.pair]) pairsMap[r.pair] = [];
      pairsMap[r.pair].push(r);
    });

    const pairsList = [];
    Object.keys(pairsMap).sort().forEach(p => {
      const records = pairsMap[p];
      if (records.length === 1) {
        pairsList.push(records[0]);
      } else {
        const mergedTeachers = records.map(r => r.fam).join('<br><hr>');
        const mergedLessons = records.map(r => r.lesson).join('<br><hr>');
        pairsList.push({
          pair: p,
          fam: mergedTeachers,
          lesson: mergedLessons
        });
      }
    });

    schedule.push({ dt, pairs: pairsList });
  });
  return schedule;
}

// ─── Renderers ───
function renderTeacherTable(schedule) {
  if (schedule.length === 0) return `<div class="empty-state"><div class="empty-state__icon"><i class="fa-regular fa-calendar-xmark"></i></div><div class="empty-state__text">Немає занять на цьому тижні</div></div>`;
  let html = '';
  schedule.forEach(day => {
    html += `<div class="day-card">
      <div class="day-card__header"><span class="day-icon"><i class="fa-regular fa-calendar-days"></i></span> ${formatDate(day.dt)}</div>
      <table class="schedule-table">
        <thead><tr><th class="col-pair">Пара</th><th class="col-middle">Групи</th><th class="col-last">Дисципліна</th></tr></thead>
        <tbody>`;
    day.pairs.forEach(p => {
      html += `<tr>
        <td><span class="pair-number">${p.pair}</span></td>
        <td class="cell-group">${p.gname}</td>
        <td class="cell-lesson">${p.lesson}</td>
      </tr>`;
    });
    html += `</tbody></table></div>`;
  });
  return html;
}

function renderGroupTable(schedule) {
  if (schedule.length === 0) return `<div class="empty-state"><div class="empty-state__icon"><i class="fa-regular fa-calendar-xmark"></i></div><div class="empty-state__text">Немає занять на цьому тижні</div></div>`;
  let html = '';
  schedule.forEach(({ dt, pairs }) => {
    html += `<div class="day-card">
      <div class="day-card__header"><span class="day-icon"><i class="fa-regular fa-calendar-days"></i></span> ${formatDate(dt)}</div>
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

// ─── Initialize ───
document.addEventListener('DOMContentLoaded', () => {
  const teachers = getUniqueTeachers(SCHEDULE_DATA).map(t => ({ value: t.tid, label: t.fam }));
  const groups = getUniqueGroups(SCHEDULE_DATA).map(g => ({ value: g.gid, label: g.gname }));
  const weeks = getUniqueWeeks(SCHEDULE_DATA);

  let currentGroupId = null;
  let currentTeacherId = null;

  // DOM Elements
  const teacherOutput = document.getElementById('teacherOutput');
  const teacherTitle = document.getElementById('teacherTitle');
  const teacherStats = document.getElementById('teacherStats');
  
  const groupOutput = document.getElementById('groupOutput');
  const groupTitle = document.getElementById('groupTitle');
  const groupStats = document.getElementById('groupStats');

  function refreshDisplays() {
    const weeklyData = filterDataByWeek(SCHEDULE_DATA);
    if (currentGroupId) {
      const schedule = buildGroupSchedule(weeklyData, currentGroupId);
      groupOutput.innerHTML = renderGroupTable(schedule);
    }
    if (currentTeacherId) {
      const schedule = buildTeacherSchedule(weeklyData, [currentTeacherId]);
      teacherOutput.innerHTML = renderTeacherTable(schedule);
    }
  }

  // ─── Setup Date Picker ───
  if (weeks.length > 0) {
    const lastWeek = weeks[weeks.length - 1];
    CURRENT_WEEK_ID = lastWeek.value;
    document.getElementById('weekSelectValue').textContent = lastWeek.label;
    
    const wrapper = document.getElementById('datePickerWrapper');
    if (wrapper && window.flatpickr) {
      const firstWeek = weeks[0];
      const minDate = new Date(firstWeek.value);
      
      const lastSunday = new Date(lastWeek.value);
      lastSunday.setDate(lastSunday.getDate() + 6);
      
      const activeWeeks = new Set(weeks.map(w => w.value));
      
      flatpickr(wrapper, {
        locale: "uk",
        minDate: minDate,
        maxDate: lastSunday,
        disableMobile: "true",
        position: "auto center",
        disable: [
          function(date) {
            let day = date.getDay();
            if (day === 0) day = 7;
            const monday = new Date(date);
            monday.setDate(date.getDate() - day + 1);
            monday.setHours(0,0,0,0);
            return !activeWeeks.has(monday.getTime());
          }
        ],
        onChange: function(selectedDates) {
          if (selectedDates.length === 0) return;
          const d = selectedDates[0];
          let day = d.getDay();
          if (day === 0) day = 7;
          const monday = new Date(d);
          monday.setDate(d.getDate() - day + 1);
          monday.setHours(0,0,0,0);
          
          CURRENT_WEEK_ID = monday.getTime();
          
          const sunday = new Date(monday);
          sunday.setDate(monday.getDate() + 6);
          
          document.getElementById('weekSelectValue').textContent = `${formatShortDate(monday)} — ${formatShortDate(sunday)}`;
          refreshDisplays();
        },
        onReady: function(selectedDates, dateStr, instance) {
          const btnContainer = document.createElement('div');
          btnContainer.style.display = 'flex';
          btnContainer.style.justifyContent = 'space-between';
          btnContainer.style.padding = '10px';
          btnContainer.style.borderTop = '1px solid rgba(255,255,255,0.1)';
          
          const clearBtn = document.createElement('button');
          clearBtn.textContent = 'Очистити';
          clearBtn.style.background = 'transparent';
          clearBtn.style.color = 'var(--text-secondary)';
          clearBtn.style.border = 'none';
          clearBtn.style.cursor = 'pointer';
          clearBtn.style.fontSize = '0.9rem';
          
          const todayBtn = document.createElement('button');
          todayBtn.textContent = 'Сьогодні';
          todayBtn.style.background = 'transparent';
          todayBtn.style.color = 'var(--accent-blue-light)';
          todayBtn.style.border = 'none';
          todayBtn.style.cursor = 'pointer';
          todayBtn.style.fontWeight = 'bold';
          todayBtn.style.fontSize = '0.9rem';

          clearBtn.addEventListener('click', () => {
            instance.clear();
            CURRENT_WEEK_ID = lastWeek.value;
            document.getElementById('weekSelectValue').textContent = lastWeek.label;
            refreshDisplays();
            instance.close();
          });

          todayBtn.addEventListener('click', () => {
            const today = new Date();
            instance.setDate(today, true);
            instance.close();
          });

          btnContainer.appendChild(clearBtn);
          btnContainer.appendChild(todayBtn);
          instance.calendarContainer.appendChild(btnContainer);
        }
      });
    }
  }

  setupCustomSelect('groupCustomSelect', 'groupSelectHeader', 'groupSelectDropdown', 'groupSelectValue', 'groupSearchInput', 'groupList', groups, (item) => {
    currentGroupId = parseInt(item.value);
    groupTitle.textContent = item.label;
    groupStats.innerHTML = renderStats(SCHEDULE_DATA, currentGroupId, 'group');
    refreshDisplays();
  });

  setupCustomSelect('teacherCustomSelect', 'teacherSelectHeader', 'teacherSelectDropdown', 'teacherSelectValue', 'teacherSearchInput', 'teacherList', teachers, (item) => {
    currentTeacherId = parseInt(item.value);
    teacherTitle.textContent = item.label;
    teacherStats.innerHTML = renderStats(SCHEDULE_DATA, currentTeacherId, 'teacher');
    refreshDisplays();
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
function setupCustomSelect(containerId, headerId, dropdownId, valueId, searchId, listId, items, onSelect) {
  const container = document.getElementById(containerId);
  const header = document.getElementById(headerId);
  const valueEl = document.getElementById(valueId);
  const searchInput = searchId ? document.getElementById(searchId) : null;
  const listEl = document.getElementById(listId);

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

  renderList();

  header.addEventListener('click', (e) => {
    e.stopPropagation();
    const isOpen = container.classList.contains('open');
    document.querySelectorAll('.custom-select').forEach(el => el.classList.remove('open'));
    if (!isOpen) {
      container.classList.add('open');
      if (searchInput) {
        searchInput.value = '';
        renderList();
        searchInput.focus();
      }
    }
  });

  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      renderList(e.target.value);
    });
  }

  document.getElementById(dropdownId).addEventListener('click', (e) => {
    e.stopPropagation();
  });
}

// Close dropdowns when clicking outside
document.addEventListener('click', () => {
  document.querySelectorAll('.custom-select').forEach(el => el.classList.remove('open'));
});

// ─── Journal Modal Logic ───
window.openJournalModal = function(type, targetId, subject) {
  let filtered = SCHEDULE_DATA.filter(r => type === 'teacher' ? r.tid === targetId : r.gid === targetId);
  filtered = filtered.filter(r => r.lesson === subject);
  
  const uniquePairs = new Map();
  filtered.forEach(r => {
    const key = `${r.dt}-${r.pair}`;
    if (!uniquePairs.has(key)) {
      uniquePairs.set(key, { ...r }); // copy
    } else {
      if (type === 'teacher') {
        const existing = uniquePairs.get(key);
        if (!existing.gname.includes(r.gname)) {
          existing.gname += `, ${r.gname}`;
        }
      }
    }
  });
  
  const sorted = Array.from(uniquePairs.values()).sort((a, b) => {
    const dta = new Date(a.dt.split(' ')[0]).getTime();
    const dtb = new Date(b.dt.split(' ')[0]).getTime();
    if (dta !== dtb) return dta - dtb;
    return a.pair - b.pair;
  });

  let html = '';
  let currentMonth = '';
  
  sorted.forEach(r => {
    const dateObj = new Date(r.dt.split(' ')[0]);
    const monthKey = dateObj.toLocaleString('uk-UA', { month: 'long', year: 'numeric' });
    if (monthKey !== currentMonth) {
      html += `<div style="padding: 0.5rem 0.8rem; background: rgba(255,255,255,0.02); font-weight: bold; color: var(--accent-yellow); margin-top: 1rem; border-radius: 4px; text-transform: capitalize;">${monthKey}</div>`;
      currentMonth = monthKey;
    }
    
    html += `
      <div class="journal-item">
        <div class="journal-date"><i class="fa-regular fa-calendar-check" style="color: var(--accent-blue-light);"></i>${formatDate(r.dt)}</div>
        <div class="journal-pair"><span class="pair-number" style="display:inline-flex; width: 22px; height: 22px; align-items:center; justify-content:center;">${r.pair}</span> пара ${type === 'teacher' ? `<br><span style="font-size:0.8rem;opacity:0.7">${r.gname}</span>` : ''}</div>
      </div>
    `;
  });

  document.getElementById('journalModalTitle').textContent = subject;
  document.getElementById('journalModalBody').innerHTML = html;
  document.getElementById('journalModal').classList.add('active');
};

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('journalModalClose').addEventListener('click', () => {
    document.getElementById('journalModal').classList.remove('active');
  });
  document.getElementById('journalModal').addEventListener('click', (e) => {
    if (e.target.id === 'journalModal') {
      document.getElementById('journalModal').classList.remove('active');
    }
  });
});
