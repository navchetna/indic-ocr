import { useState, useCallback, useEffect } from 'react';
import Sidebar from './components/Sidebar.jsx';
import UploadForm from './components/UploadForm.jsx';
import ResultView from './components/ResultView.jsx';
import Header from './components/Header.jsx';
import { submitSingleOCR, listRecentTasks, fetchTaskResult, findAnnotatedImage } from './api/ocr.js';
import './App.css';

const LANGUAGES = [
  { code: 'hi', name: 'Hindi', script: 'Devanagari' },
  { code: 'mr', name: 'Marathi', script: 'Devanagari' },
  { code: 'te', name: 'Telugu', script: 'Telugu' },
  { code: 'ta', name: 'Tamil', script: 'Tamil' },
  { code: 'ml', name: 'Malayalam', script: 'Malayalam' },
];

export default function App() {
  const [mode, setMode] = useState('single'); // 'single' | 'batch'
  const [tasks, setTasks] = useState([]);
  const [selectedTask, setSelectedTask] = useState(null);
  const [taskResult, setTaskResult] = useState(null);
  const [annotatedImageUrl, setAnnotatedImageUrl] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Load recent tasks
  const refreshTasks = useCallback(async () => {
    try {
      const items = await listRecentTasks(mode, 10);
      setTasks(items);
    } catch {
      // Silently fail — outputs dir may not exist yet
      setTasks([]);
    }
  }, [mode]);

  useEffect(() => {
    refreshTasks();
  }, [refreshTasks]);

  // Handle selecting a task
  const handleSelectTask = useCallback(async (task) => {
    setSelectedTask(task);
    setError(null);
    try {
      const [result, imgUrl] = await Promise.all([
        fetchTaskResult(task.path),
        findAnnotatedImage(task.path),
      ]);
      setTaskResult(result);
      setAnnotatedImageUrl(imgUrl);
    } catch (e) {
      setError(`Failed to load task: ${e.message}`);
      setTaskResult(null);
      setAnnotatedImageUrl(null);
    }
  }, []);

  // Handle form submission
  const handleSubmit = useCallback(
    async (file, lang) => {
      setIsProcessing(true);
      setError(null);
      setTaskResult(null);
      setAnnotatedImageUrl(null);
      setSelectedTask(null);

      try {
        const result = await submitSingleOCR(file, lang);

        // After processing, refresh the task list and display result inline
        await refreshTasks();

        // Try to find the newly created task
        const updatedTasks = await listRecentTasks(mode, 10);
        setTasks(updatedTasks);

        if (updatedTasks.length > 0) {
          // Select the most recent task
          const newest = updatedTasks[0];
          setSelectedTask(newest);
          const [fullResult, imgUrl] = await Promise.all([
            fetchTaskResult(newest.path),
            findAnnotatedImage(newest.path),
          ]);
          setTaskResult(fullResult);
          setAnnotatedImageUrl(imgUrl);
        } else {
          // Fallback: display from the API response directly
          setTaskResult({
            filename: result.filename,
            language: result.language,
            processing_time_seconds: result.processing_time_seconds,
            results: [],
            full_text: result.extracted_text,
          });
        }
      } catch (e) {
        setError(e.message || 'Processing failed');
      } finally {
        setIsProcessing(false);
      }
    },
    [mode, refreshTasks]
  );

  return (
    <div className="app-layout">
      <Sidebar
        mode={mode}
        onModeChange={setMode}
        tasks={tasks}
        selectedTask={selectedTask}
        onSelectTask={handleSelectTask}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />

      <div className={`main-area ${sidebarOpen ? '' : 'sidebar-collapsed'}`}>
        <Header onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} sidebarOpen={sidebarOpen} />

        <main className="main-content">
          {/* Upload form — always visible at top when no result */}
          {!selectedTask && !isProcessing && (
            <UploadForm
              languages={LANGUAGES}
              onSubmit={handleSubmit}
              disabled={isProcessing}
              mode={mode}
            />
          )}

          {/* Processing indicator */}
          {isProcessing && (
            <div className="processing-card">
              <div className="spinner" />
              <div className="processing-text">
                <h3>Processing image…</h3>
                <p>This may take a few minutes depending on image size.</p>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="error-card">
              <span className="error-icon">!</span>
              <span>{error}</span>
              <button className="error-dismiss" onClick={() => setError(null)}>×</button>
            </div>
          )}

          {/* Results */}
          {taskResult && !isProcessing && (
            <ResultView
              result={taskResult}
              annotatedImageUrl={annotatedImageUrl}
              onBack={() => {
                setSelectedTask(null);
                setTaskResult(null);
                setAnnotatedImageUrl(null);
              }}
            />
          )}
        </main>
      </div>
    </div>
  );
}
