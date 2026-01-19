import React, { useState, useEffect, useCallback } from 'react';
import { Task, TaskCategory } from './types';
import { TaskForm } from './components/TaskForm';
import { TaskList } from './components/TaskList';
import { useTaskScheduler } from './hooks/useTaskScheduler';
import { categorizeTask, getDailySummary } from './services/gemini';
import { Sparkles, Bot } from 'lucide-react';

const STORAGE_KEY = 'ai_smart_assistant_tasks';

const App: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [summary, setSummary] = useState<string | null>(null);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [isAdding, setIsAdding] = useState(false);

  // Load from local storage
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        setTasks(JSON.parse(saved));
      } catch (e) {
        console.error("Failed to load tasks", e);
      }
    }
  }, []);

  // Save to local storage
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
  }, [tasks]);

  // Hook for notifications
  useTaskScheduler(tasks);

  const handleAddTask = async (content: string, date: Date, repeatDays: number[]) => {
    setIsAdding(true);
    // AI categorization
    const category = await categorizeTask(content);
    
    const newTask: Task = {
      id: crypto.randomUUID(),
      content,
      remindTime: date.toISOString(),
      repeatDays,
      category,
      isActive: true,
      isCompleted: false,
      createdAt: Date.now(),
    };

    setTasks(prev => [...prev, newTask]);
    setIsAdding(false);
  };

  const toggleTask = useCallback((id: string) => {
    setTasks(prev => prev.map(t => 
      t.id === id ? { ...t, isCompleted: !t.isCompleted } : t
    ));
  }, []);

  const deleteTask = useCallback((id: string) => {
    setTasks(prev => prev.filter(t => t.id !== id));
  }, []);

  const generateSummary = async () => {
    setIsSummarizing(true);
    // Filter tasks for "today" (simple check) or just all active tasks for simplicity in this demo
    const activeTasks = tasks.filter(t => !t.isCompleted);
    const result = await getDailySummary(activeTasks);
    setSummary(result);
    setIsSummarizing(false);
  };

  return (
    <div className="min-h-screen bg-[#f9fafb] text-gray-900 pb-20">
      <div className="max-w-2xl mx-auto px-6 py-10">
        
        {/* Header */}
        <div className="flex items-center justify-between mb-10">
          <div>
            <h1 className="text-3xl font-light tracking-tight text-gray-900">早安，開發者。</h1>
            <p className="text-gray-500 mt-1 text-sm font-light">今天是 {new Date().toLocaleDateString('zh-TW', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })}</p>
          </div>
          <button 
            onClick={generateSummary}
            disabled={isSummarizing}
            className="group flex items-center gap-2 bg-white hover:bg-gray-50 border border-gray-200 px-4 py-2 rounded-xl transition-all shadow-sm hover:shadow-md disabled:opacity-50"
          >
            <Bot size={20} className={isSummarizing ? 'animate-pulse text-blue-500' : 'text-gray-600'} />
            <span className="text-sm font-medium text-gray-700">AI 今日摘要</span>
          </button>
        </div>

        {/* AI Summary Card */}
        {summary && (
          <div className="bg-gradient-to-br from-indigo-50 to-blue-50 border border-indigo-100 p-6 rounded-2xl mb-8 relative overflow-hidden animate-in fade-in slide-in-from-top-4 duration-500">
            <div className="absolute top-0 right-0 p-4 opacity-10">
              <Sparkles size={100} />
            </div>
            <h3 className="text-indigo-900 font-medium mb-2 flex items-center gap-2">
              <Sparkles size={16} className="text-indigo-500"/> 
              秘書摘要
            </h3>
            <div className="text-indigo-800 text-sm leading-relaxed whitespace-pre-line">
              {summary}
            </div>
          </div>
        )}

        {/* Task Input */}
        <TaskForm onAdd={handleAddTask} isProcessing={isAdding} />

        {/* Tasks */}
        <div className="mt-8">
           <div className="flex items-center justify-between mb-4">
             <h2 className="text-xl font-medium text-gray-800">待辦事項</h2>
             <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded-full">
               {tasks.filter(t => !t.isCompleted).length} 待完成
             </span>
           </div>
           <TaskList 
             tasks={tasks}
             onToggleComplete={toggleTask}
             onDelete={deleteTask}
           />
        </div>

      </div>
    </div>
  );
};

export default App;