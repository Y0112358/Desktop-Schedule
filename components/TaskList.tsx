import React from 'react';
import { Task, TaskCategory, DAYS_OF_WEEK } from '../types';
import { CheckCircle2, Circle, Trash2, Clock, CalendarDays } from 'lucide-react';

interface TaskListProps {
  tasks: Task[];
  onToggleComplete: (id: string) => void;
  onDelete: (id: string) => void;
}

const CategoryBadge: React.FC<{ category: TaskCategory }> = ({ category }) => {
  const colors = {
    [TaskCategory.RESEARCH]: 'bg-blue-100 text-blue-700',
    [TaskCategory.ADMIN]: 'bg-purple-100 text-purple-700',
    [TaskCategory.PERSONAL]: 'bg-green-100 text-green-700',
    [TaskCategory.OTHER]: 'bg-gray-100 text-gray-700',
  };

  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${colors[category]}`}>
      {category}
    </span>
  );
};

export const TaskList: React.FC<TaskListProps> = ({ tasks, onToggleComplete, onDelete }) => {
  if (tasks.length === 0) {
    return (
      <div className="text-center py-10 text-gray-400">
        <p>目前沒有任務。</p>
      </div>
    );
  }

  // Sort: Incomplete first, then by time
  const sortedTasks = [...tasks].sort((a, b) => {
    if (a.isCompleted !== b.isCompleted) return a.isCompleted ? 1 : -1;
    return new Date(a.remindTime).getTime() - new Date(b.remindTime).getTime();
  });

  return (
    <div className="space-y-3">
      {sortedTasks.map(task => {
        const date = new Date(task.remindTime);
        const timeString = date.toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit', hour12: false });
        const dateString = date.toLocaleDateString('zh-TW', { month: 'short', day: 'numeric' });
        
        const repeatLabels = task.repeatDays.map(d => DAYS_OF_WEEK.find(day => day.value === d)?.label).filter(Boolean).join(', ');

        return (
          <div 
            key={task.id} 
            className={`group bg-white rounded-xl p-4 shadow-sm border border-gray-100 flex items-center justify-between transition-all hover:shadow-md ${task.isCompleted ? 'opacity-50' : ''}`}
          >
            <div className="flex items-center gap-4 overflow-hidden">
              <button 
                onClick={() => onToggleComplete(task.id)}
                className={`flex-shrink-0 transition-colors ${task.isCompleted ? 'text-green-500' : 'text-gray-300 hover:text-gray-400'}`}
              >
                {task.isCompleted ? <CheckCircle2 size={24} /> : <Circle size={24} />}
              </button>
              
              <div className="flex flex-col min-w-0">
                <div className="flex items-center gap-2 mb-1">
                   <span className={`font-medium text-gray-900 truncate ${task.isCompleted ? 'line-through text-gray-400' : ''}`}>
                    {task.content}
                  </span>
                  <CategoryBadge category={task.category} />
                </div>
                
                <div className="flex items-center text-xs text-gray-500 gap-3">
                  <span className="flex items-center gap-1">
                    <Clock size={12} />
                    {timeString}
                  </span>
                  {task.repeatDays.length > 0 ? (
                    <span className="flex items-center gap-1 text-blue-600">
                      <CalendarDays size={12} />
                       每{repeatLabels}
                    </span>
                  ) : (
                    <span className="flex items-center gap-1">
                      <CalendarDays size={12} />
                      {dateString}
                    </span>
                  )}
                </div>
              </div>
            </div>

            <button 
              onClick={() => onDelete(task.id)}
              className="text-gray-300 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity p-2"
            >
              <Trash2 size={18} />
            </button>
          </div>
        );
      })}
    </div>
  );
};