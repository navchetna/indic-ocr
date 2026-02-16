import { useState } from 'react';
import { ChevronLeft, ChevronDown, FileText, FolderOpen, Clock } from 'lucide-react';
import './Sidebar.css';

export default function Sidebar({ mode, onModeChange, tasks, selectedTask, onSelectTask, isOpen, onToggle }) {
  const [expandedLangs, setExpandedLangs] = useState({
    hi: true,
    mr: false,
    te: true,
    ta: false,
    ml: false,
  });

  // Parse task dirname to extract label info
  const formatTaskLabel = (task) => {
    // dirname format: YYYYMMDD_HHMMSS_filestem
    const parts = task.dirName.split('_');
    if (parts.length >= 3) {
      const date = parts[0]; // YYYYMMDD
      const time = parts[1]; // HHMMSS
      const stem = parts.slice(2).join('_');
      const dateStr = `${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6, 8)}`;
      const timeStr = `${time.slice(0, 2)}:${time.slice(2, 4)}`;
      return { name: stem, date: dateStr, time: timeStr };
    }
    return { name: task.dirName, date: '', time: '' };
  };

  const langLabel = (code) => {
    const map = { hi: 'Hindi', mr: 'Marathi', te: 'Telugu', ta: 'Tamil', ml: 'Malayalam' };
    return map[code] || code;
  };

  const toggleLang = (lang) => {
    setExpandedLangs((prev) => ({ ...prev, [lang]: !prev[lang] }));
  };

  // Group tasks by language
  const tasksByLang = {
    hi: tasks.filter((t) => t.lang === 'hi'),
    mr: tasks.filter((t) => t.lang === 'mr'),
    te: tasks.filter((t) => t.lang === 'te'),
    ta: tasks.filter((t) => t.lang === 'ta'),
    ml: tasks.filter((t) => t.lang === 'ml'),
  };

  const languages = ['hi', 'mr', 'te', 'ta', 'ml'];

  if (!isOpen) return null;

  return (
    <aside className="sidebar">
      {/* Header */}
      <div className="sidebar-header">
        <div className="sidebar-brand">
          <div className="sidebar-brand-icon">O</div>
          <span className="sidebar-brand-text">IndicOCR</span>
        </div>
        <button className="sidebar-close" onClick={onToggle} title="Close sidebar">
          <ChevronLeft size={18} />
        </button>
      </div>

      {/* Mode Toggle */}
      <div className="sidebar-section">
        <label className="sidebar-label">Processing Mode</label>
        <div className="mode-toggle">
          <button
            className={`mode-btn ${mode === 'single' ? 'active' : ''}`}
            onClick={() => onModeChange('single')}
          >
            <FileText size={15} />
            Single
          </button>
          <button
            className={`mode-btn ${mode === 'batch' ? 'active' : ''}`}
            onClick={() => onModeChange('batch')}
          >
            <FolderOpen size={15} />
            Batch
          </button>
        </div>
      </div>

      {/* Divider */}
      <div className="sidebar-divider" />

      {/* Task List */}
      <div className="sidebar-section sidebar-tasks">
        <label className="sidebar-label">
          <Clock size={14} />
          Recent Tasks
          <span className="task-count">{tasks.length}</span>
        </label>

        {mode === 'batch' && (
          <div className="batch-placeholder">
            <FolderOpen size={24} strokeWidth={1.5} />
            <p>Batch processing</p>
            <span>Coming soon</span>
          </div>
        )}

        {mode === 'single' && tasks.length === 0 && (
          <div className="empty-tasks">
            <FileText size={24} strokeWidth={1.5} />
            <p>No tasks yet</p>
            <span>Upload an image to get started</span>
          </div>
        )}

        {mode === 'single' && tasks.length > 0 && (
          <div className="language-sections">
            {languages.map((lang) => {
              const langTasks = tasksByLang[lang];
              const isExpanded = expandedLangs[lang];

              return (
                <div key={lang} className="lang-section">
                  <button
                    className={`lang-section-header ${isExpanded ? 'expanded' : ''}`}
                    onClick={() => toggleLang(lang)}
                  >
                    <ChevronDown size={16} className="lang-chevron" />
                    <span className="lang-section-title">{langLabel(lang)}</span>
                    <span className="lang-task-count">{langTasks.length}</span>
                  </button>

                  {isExpanded && (
                    <div className="lang-section-tasks">
                      {langTasks.length === 0 ? (
                        <div className="empty-lang-tasks">
                          <span>No tasks</span>
                        </div>
                      ) : (
                        <div className="task-list">
                          {langTasks.map((task) => {
                            const { name, date, time } = formatTaskLabel(task);
                            const isSelected = selectedTask?.id === task.id;

                            return (
                              <button
                                key={task.id}
                                className={`task-item ${isSelected ? 'selected' : ''}`}
                                onClick={() => onSelectTask(task)}
                              >
                                <div className="task-item-main">
                                  <span className="task-name" title={name}>
                                    {name}
                                  </span>
                                </div>
                                <div className="task-item-meta">
                                  <span>{date}</span>
                                  <span>{time}</span>
                                </div>
                              </button>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </aside>
  );
}
