import { useEffect, useRef } from 'react';
import { Task } from '../types';

export const useTaskScheduler = (tasks: Task[]) => {
  const notifiedTasks = useRef<Set<string>>(new Set());

  // Request notification permission on mount
  useEffect(() => {
    if ('Notification' in window && Notification.permission !== 'granted') {
      Notification.requestPermission();
    }
  }, []);

  useEffect(() => {
    const checkTasks = () => {
      const now = new Date();
      
      tasks.forEach(task => {
        if (!task.isActive || task.isCompleted) return;

        const taskTime = new Date(task.remindTime);
        const timeDiff = taskTime.getTime() - now.getTime();

        // Trigger if time is within the last minute (to avoid missing it) and hasn't been notified yet
        // Allowing a 60 second window
        if (timeDiff <= 0 && timeDiff > -60000) {
            const notificationKey = `${task.id}-${taskTime.getTime()}`;
            
            if (!notifiedTasks.current.has(notificationKey)) {
                // Check repeat days if needed
                const currentDay = now.getDay();
                const isRecurringToday = task.repeatDays.length > 0 && task.repeatDays.includes(currentDay);
                const isOneTime = task.repeatDays.length === 0;

                // Simple logic: if it's a specific date match OR (it's recurring and time matches)
                // For recurring, remindTime usually holds the *time*, date might be old.
                // Here we simplify: User sets a full DateTime. 
                // If recurring, we check only Hour/Minute match.
                
                let shouldNotify = false;
                
                if (isOneTime) {
                    shouldNotify = true;
                } else if (isRecurringToday) {
                    // Check only HH:MM
                    if (taskTime.getHours() === now.getHours() && taskTime.getMinutes() === now.getMinutes()) {
                        shouldNotify = true;
                    }
                }

                if (shouldNotify) {
                    if ('Notification' in window && Notification.permission === 'granted') {
                        new Notification("AI Smart Assistant 提醒", {
                            body: task.content,
                            icon: "https://picsum.photos/64/64" // Placeholder icon
                        });
                    }
                    notifiedTasks.current.add(notificationKey);
                }
            }
        }
      });
    };

    const intervalId = setInterval(checkTasks, 1000); // Check every second
    return () => clearInterval(intervalId);
  }, [tasks]);
};