import { GoogleGenAI, Type } from "@google/genai";
import { Task, TaskCategory } from "../types";

const GEMINI_MODEL = 'gemini-3-flash-preview';

const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

export const getDailySummary = async (tasks: Task[]): Promise<string> => {
  if (tasks.length === 0) {
    return "目前沒有待辦事項。享受這美好的一天吧！";
  }

  const taskDescriptions = tasks
    .filter(t => !t.isCompleted)
    .map(t => `- ${t.content} (${new Date(t.remindTime).toLocaleTimeString('zh-TW', {hour: '2-digit', minute:'2-digit'})})`)
    .join('\n');

  const prompt = `
    你是一位專業的職場秘書。請閱讀以下今天的待辦事項，並以繁體中文撰寫一段 100 字以內的「今日重點摘要」。
    語氣要專業、溫柔且充滿活力。
    在摘要之後，請附上一句簡短的職場鼓勵語。

    待辦事項清單：
    ${taskDescriptions}
  `;

  try {
    const response = await ai.models.generateContent({
      model: GEMINI_MODEL,
      contents: prompt,
    });
    return response.text || "無法生成摘要。";
  } catch (error) {
    console.error("Error generating summary:", error);
    return "連線發生錯誤，無法生成摘要。";
  }
};

export const categorizeTask = async (content: string): Promise<TaskCategory> => {
  const prompt = `
    請將以下任務歸類為其中一個類別：研發, 行政, 個人, 其他。
    任務內容：${content}
    
    只需回傳類別名稱，不要有其他文字。
  `;

  try {
    const response = await ai.models.generateContent({
      model: GEMINI_MODEL,
      contents: prompt,
      config: {
        responseMimeType: 'application/json',
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            category: {
              type: Type.STRING,
              enum: ['研發', '行政', '個人', '其他']
            }
          }
        }
      }
    });

    const result = JSON.parse(response.text || '{}');
    const categoryStr = result.category;

    switch (categoryStr) {
      case '研發': return TaskCategory.RESEARCH;
      case '行政': return TaskCategory.ADMIN;
      case '個人': return TaskCategory.PERSONAL;
      default: return TaskCategory.OTHER;
    }
  } catch (error) {
    console.warn("Categorization failed, defaulting to Other", error);
    return TaskCategory.OTHER;
  }
};