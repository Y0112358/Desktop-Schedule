import React, { useState } from 'react';
import { DAYS_OF_WEEK } from '../types';
import { Plus, Clock, Calendar } from 'lucide-react';

interface TaskFormProps {
  onAdd: (content: string, date: Date, repeatDays: number[]) => void;
  isProcessing: boolean;
}

export const TaskForm: React.FC<TaskFormProps> = ({ onAdd, isProcessing }) => {
  const [content, setContent] = useState('');
  // Default to today
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  // Default to next hour
  const now = new Date();
  now.setHours(now.getHours() + 1, 0, 0, 0);
  const [time, setTime] = useState(now.toTimeString().slice(0, 5));
  
  const [repeatDays, setRepeatDays] = useState<number[]>([]);
  const [showRepeatOptions, setShowRepeatOptions] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;

    const selectedDateTime = new Date(`${date}T${time}`);
    onAdd(content, selectedDateTime, repeatDays);
    
    // Reset content but keep basic settings for quick entry
    setContent('');
  };

  const toggleDay = (day: number) => {
    setRepeatDays(prev => 
      prev.includes(day) ? prev.filter(d => d !== day) : [...prev, day]
    );
  };

  const setQuickTime = (type: 'hour' | 'tomorrow') => {
    const d = new Date();
    if (type === 'hour') {
      d.setHours(d.getHours() + 1);
      d.setMinutes(0);
      setDate(d.toISOString().split('T')[0]);
      setTime(d.toTimeString().slice(0, 5));
    } else {
      d.setDate(d.getDate() + 1);
      d.setHours(9, 0, 0, 0);
      setDate(d.toISOString().split('T')[0]);
      setTime('09:00');
    }
  };

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 mb-6">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <input
            type="text"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="輸入待辦事項 (例如：3D DRAM 研發進度會議)..."
            className="w-full text-lg font-medium text-gray-800 placeholder-gray-400 border-b-2 border-gray-100 focus:border-gray-800 outline-none py-2 bg-transparent transition-colors"
            autoFocus
          />
        </div>

        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2 bg-gray-50 px-3 py-2 rounded-lg text-sm text-gray-600">
             <Calendar size={16} />
             <input 
               type="date" 
               value={date}
               onChange={(e) => setDate(e.target.value)}
               className="bg-transparent outline-none cursor-pointer"
             />
          </div>
          
          <div className="flex items-center gap-2 bg-gray-50 px-3 py-2 rounded-lg text-sm text-gray-600">
             <Clock size={16} />
             <input 
               type="time" 
               value={time}
               onChange={(e) => setTime(e.target.value)}
               className="bg-transparent outline-none cursor-pointer"
             />
          </div>

          <div className="flex items-center gap-2">
            <button type="button" onClick={() => setQuickTime('hour')} className="text-xs font-medium text-gray-500 hover:text-gray-900 bg-gray-100 hover:bg-gray-200 px-3 py-1.5 rounded-md transition-colors">
              1小時後
            </button>
            <button type="button" onClick={() => setQuickTime('tomorrow')} className="text-xs font-medium text-gray-500 hover:text-gray-900 bg-gray-100 hover:bg-gray-200 px-3 py-1.5 rounded-md transition-colors">
              明天早上
            </button>
          </div>
        </div>

        <div>
           <button 
             type="button"
             onClick={() => setShowRepeatOptions(!showRepeatOptions)}
             className={`text-xs font-medium mb-2 flex items-center gap-1 transition-colors ${repeatDays.length > 0 ? 'text-blue-600' : 'text-gray-400 hover:text-gray-600'}`}
           >
             {repeatDays.length > 0 ? '重複週期：已設定' : '+ 設定重複週期'}
           </button>
           
           {showRepeatOptions && (
             <div className="flex flex-wrap gap-2 animate-in fade-in slide-in-from-top-2 duration-200">
               {DAYS_OF_WEEK.map(day => (
                 <label key={day.value} className="cursor-pointer">
                   <input 
                     type="checkbox" 
                     className="hidden peer"
                     checked={repeatDays.includes(day.value)}
                     onChange={() => toggleDay(day.value)}
                   />
                   <div className="px-3 py-1 rounded-full text-xs border border-gray-200 text-gray-500 peer-checked:bg-gray-800 peer-checked:text-white peer-checked:border-gray-800 transition-all select-none">
                     {day.label}
                   </div>
                 </label>
               ))}
             </div>
           )}
        </div>

        <div className="flex justify-end pt-2">
          <button
            type="submit"
            disabled={isProcessing || !content.trim()}
            className="bg-gray-900 text-white hover:bg-black disabled:bg-gray-300 disabled:cursor-not-allowed px-6 py-2.5 rounded-xl text-sm font-medium transition-all shadow-lg hover:shadow-xl flex items-center gap-2"
          >
            {isProcessing ? (
                <span>AI 分類中...</span>
            ) : (
                <>
                    <Plus size={18} />
                    <span>新增任務</span>
                </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};