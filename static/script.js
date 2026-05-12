/* =============================================================
   ResumeAI — Frontend JavaScript
   Handles: dark mode, drag-and-drop, form validation,
   analyzer submission, auto-dismiss flashes.
   ============================================================= */

document.addEventListener('DOMContentLoaded', () => {

  // ===========================================================
  // 1. DARK MODE
  // ===========================================================
  const html       = document.documentElement;
  const toggleBtn  = document.getElementById('dark-toggle');

  // Apply saved preference immediately (also applied via inline script
  // if needed, but this handles CDN Tailwind case)
  const saved = localStorage.getItem('theme');
  if (saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    html.classList.add('dark');
  }

  toggleBtn?.addEventListener('click', () => {
    html.classList.toggle('dark');
    localStorage.setItem('theme', html.classList.contains('dark') ? 'dark' : 'light');
  });


  // ===========================================================
  // 2. AUTO-DISMISS FLASH TOASTS (after 5 s)
  // ===========================================================
  const flashes = document.querySelectorAll('.flash-toast');
  flashes.forEach((el, i) => {
    setTimeout(() => {
      el.style.opacity    = '0';
      el.style.transform  = 'translateX(24px)';
      el.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
      setTimeout(() => el.remove(), 350);
    }, 5000 + i * 300);
  });


  // ===========================================================
  // 3. ANALYZER PAGE — drag-and-drop + file validation
  // ===========================================================
  const dropZone    = document.getElementById('drop-zone');
  const fileInput   = document.getElementById('file-upload');
  const uploadPrompt= document.getElementById('upload-prompt');
  const fileSelected= document.getElementById('file-selected');
  const fileNameEl  = document.getElementById('file-name');
  const fileSizeEl  = document.getElementById('file-size');
  const removeBtn   = document.getElementById('remove-file');
  const jdTextarea  = document.getElementById('job-description');
  const charCount   = document.getElementById('char-count');
  const submitBtn   = document.getElementById('submit-btn');
  const analyzerForm= document.getElementById('analyzer-form');
  const sampleBtn   = document.getElementById('sample-jd-btn');
  const skillCount  = document.getElementById('skill-highlight-count');
  const detectCount = document.getElementById('detected-count');
  const progressSteps= document.querySelectorAll('.progress-step');

  // ---- File display / toggle --------------------------------
  function showFile(file) {
    if (!file) return;
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['pdf', 'docx'].includes(ext)) {
      alert('Only PDF and DOCX files are accepted.');
      resetFile();
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      alert('File size exceeds the 2 MB limit.');
      resetFile();
      return;
    }
    if (fileNameEl)  fileNameEl.textContent  = file.name;
    if (fileSizeEl)  fileSizeEl.textContent  = `${(file.size / 1024).toFixed(1)} KB`;
    uploadPrompt?.classList.add('hidden');
    fileSelected?.classList.remove('hidden');
    checkReady();
  }

  function resetFile() {
    if (fileInput)   fileInput.value        = '';
    uploadPrompt?.classList.remove('hidden');
    fileSelected?.classList.add('hidden');
    checkReady();
  }

  function checkReady() {
    if (!submitBtn) return;
    const hasFile = fileInput?.files?.length > 0;
    const hasJD   = jdTextarea?.value?.trim().length > 0;
    submitBtn.disabled = !(hasFile && hasJD);
  }

  fileInput?.addEventListener('change', () => showFile(fileInput.files[0]));
  removeBtn?.addEventListener('click', e => { e.stopPropagation(); resetFile(); });

  // ---- Drag and drop ----------------------------------------
  if (dropZone) {
    dropZone.addEventListener('dragover', e => {
      e.preventDefault();
      dropZone.classList.add('drag-over');
    });
    ['dragleave', 'dragend'].forEach(ev =>
      dropZone.addEventListener(ev, () => dropZone.classList.remove('drag-over'))
    );
    dropZone.addEventListener('drop', e => {
      e.preventDefault();
      dropZone.classList.remove('drag-over');
      const dt = e.dataTransfer;
      if (dt.files.length) {
        // Set files on the hidden input
        const dt2 = new DataTransfer();
        dt2.items.add(dt.files[0]);
        fileInput.files = dt2.files;
        showFile(dt.files[0]);
      }
    });
  }

  // ---- JD textarea char counter + skill-count ---------------
  // Simple list of common skills to highlight in JD (first 30 to keep it fast)
  const QUICK_SKILLS = [
    'python','javascript','react','node','java','c++','aws','docker','sql',
    'mongodb','postgresql','kubernetes','typescript','django','flask','fastapi',
    'tensorflow','pytorch','machine learning','data science','devops',
    'golang','rust','swift','kotlin','flutter','angular','vue','nextjs','graphql'
  ];

  jdTextarea?.addEventListener('input', () => {
    if (charCount) charCount.textContent = jdTextarea.value.length;
    checkReady();

    // Skill counter
    const lower = jdTextarea.value.toLowerCase();
    const found  = QUICK_SKILLS.filter(s => lower.includes(s)).length;
    if (skillCount && detectCount) {
      if (found > 0) {
        detectCount.textContent = found;
        skillCount.classList.remove('hidden');
      } else {
        skillCount.classList.add('hidden');
      }
    }
  });

  // ---- Sample JD button -------------------------------------
  sampleBtn?.addEventListener('click', () => {
    if (typeof SAMPLE_JD !== 'undefined' && jdTextarea) {
      jdTextarea.value = SAMPLE_JD;
      jdTextarea.dispatchEvent(new Event('input'));
    }
  });

  // ---- Form submission → show progress steps ----------------
  analyzerForm?.addEventListener('submit', e => {
    if (submitBtn?.disabled) { e.preventDefault(); return; }

    // Show loader
    const btnContent = document.getElementById('btn-content');
    const btnLoader  = document.getElementById('btn-loader');
    btnContent?.classList.add('hidden');
    btnLoader?.classList.remove('hidden');
    submitBtn.disabled = true;

    // Animate progress steps
    const progressContainer = document.getElementById('progress-steps');
    if (progressContainer && progressSteps.length) {
      progressContainer.classList.remove('hidden');
      let idx = 0;
      const tick = setInterval(() => {
        if (idx > 0) {
          progressSteps[idx - 1].classList.add('completed');
        }
        if (idx < progressSteps.length) {
          progressSteps[idx].classList.add('active');
          idx++;
        } else {
          clearInterval(tick);
        }
      }, 700);
    }
  });


  // ===========================================================
  // 4. RESULT PAGE — score gauge + progress bars
  //    (also handled inline in result.html but
  //     we double-check here as a safety net)
  // ===========================================================
  const scoreArc     = document.getElementById('score-arc');
  const scoreDisplay = document.getElementById('score-display');

  if (scoreArc && scoreDisplay && !scoreDisplay.dataset.animated) {
    scoreDisplay.dataset.animated = '1';
    const score       = parseFloat(scoreArc.dataset.score) || 0;
    const color       = scoreArc.dataset.color || 'indigo';
    const colorMap    = { green:'#10b981', yellow:'#f59e0b', orange:'#f97316', red:'#ef4444' };
    const circumference = 402.1;

    scoreArc.style.stroke              = colorMap[color] || '#6366f1';
    scoreArc.style.transition          = 'stroke-dashoffset 1.4s cubic-bezier(0.4,0,0.2,1)';

    requestAnimationFrame(() => {
      setTimeout(() => {
        scoreArc.style.strokeDashoffset = circumference * (1 - score / 100);
      }, 100);
    });

    // Counter
    let current = 0;
    const step  = score / 60;
    const timer = setInterval(() => {
      current = Math.min(current + step, score);
      scoreDisplay.textContent = Math.round(current) + '%';
      if (current >= score) clearInterval(timer);
    }, 16);
  }

  // Score bars
  document.querySelectorAll('.score-bar').forEach(bar => {
    if (bar.dataset.animated) return;
    bar.dataset.animated = '1';
    const target = parseFloat(bar.dataset.target) || 0;
    setTimeout(() => { bar.style.width = target + '%'; }, 400);
  });

});