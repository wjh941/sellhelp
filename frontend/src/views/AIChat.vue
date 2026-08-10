<template>
  <div class="ai-chat-container">
    <el-row :gutter="20" style="height: calc(100vh - 180px);">
      <el-col :span="6">
        <div class="page-card" style="height: 100%; display: flex; flex-direction: column;">
          <h3 style="margin-bottom: 15px;">💬 会话历史</h3>
          <div style="flex: 1; overflow-y: auto;">
            <div
              v-for="session in sessions"
              :key="session.session_id"
              class="session-item"
              :class="{ active: session.session_id === currentSession }"
              @click="selectSession(session.session_id)"
            >
              <div class="session-preview">{{ session.last_message }}</div>
              <div class="session-time">{{ session.updated_at }}</div>
            </div>
            <el-empty v-if="sessions.length === 0" description="暂无会话" :image-size="60" />
          </div>
          <el-button type="primary" @click="newSession" style="margin-top: 10px;">
            <el-icon><Plus /></el-icon>新会话
          </el-button>
        </div>
      </el-col>

      <el-col :span="18">
        <div class="page-card chat-main" style="height: 100%; display: flex; flex-direction: column;">
          <div class="chat-header">
            <h3>🤖 盈泰生意顾问 AI</h3>
            <el-tag type="info" size="small">结合副食行业套路 + 盈泰经营数据</el-tag>
          </div>

          <div class="chat-messages" ref="messagesRef">
            <div v-if="messages.length === 0" class="welcome-message">
              <el-icon style="font-size: 48px; color: #409EFF; margin-bottom: 15px;"><ChatDotRound /></el-icon>
              <h2>您好，盈泰老板！</h2>
              <p>我是您的专属生意顾问，专注于副食批发行业。</p>
              <p>我可以结合您的经营数据，回答您关于：</p>
              <div class="suggestion-list">
                <el-tag
                  v-for="q in suggestedQuestions"
                  :key="q"
                  class="suggestion-tag"
                  @click="askSuggestion(q)"
                >{{ q }}</el-tag>
              </div>
              <p style="color: #909399; margin-top: 15px;">试试点击上面的建议提问，或者直接输入您的问题吧！</p>
            </div>

            <div v-for="(msg, idx) in messages" :key="idx" class="message-row" :class="msg.role">
              <div class="message-avatar">
                <el-avatar v-if="msg.role === 'user'" :size="36" style="background: #409EFF;">盈</el-avatar>
                <el-avatar v-else :size="36" style="background: #67C23A;">AI</el-avatar>
              </div>
              <div class="message-content">
                <div v-if="msg.role === 'assistant'" class="ai-answer" v-html="formatAnswer(msg.content)"></div>
                <div v-else class="user-question">{{ msg.content }}</div>
              </div>
            </div>

            <div v-if="loading" class="message-row assistant">
              <div class="message-avatar">
                <el-avatar :size="36" style="background: #67C23A;">AI</el-avatar>
              </div>
              <div class="message-content">
                <div class="loading-dots">
                  <span></span><span></span><span></span>
                </div>
              </div>
            </div>
          </div>

          <div class="chat-input">
            <el-input
              v-model="inputQuestion"
              type="textarea"
              :rows="2"
              placeholder="请输入您的经营问题，如：怎么稳住老客户不让客户跑同行？"
              @keydown.enter.exact.prevent="sendQuestion"
              :disabled="loading"
            />
            <el-button type="primary" @click="sendQuestion" :loading="loading" style="margin-top: 10px;">
              <el-icon><Promotion /></el-icon>发送
            </el-button>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { aiAsk, getAISessions, getAISession, deleteAISession } from '@/api'

const sessions = ref([])
const currentSession = ref(null)
const messages = ref([])
const inputQuestion = ref('')
const loading = ref(false)
const messagesRef = ref(null)

const suggestedQuestions = [
  '怎么稳住老客户，不让客户跑同行？',
  '礼盒淡季压货怎么清不亏钱？',
  '怎么利用晨升膳食大客户拉高整体利润？',
  '哪些商品适合做引流、哪些适合做利润？',
  '批发市场怎么定价不丢单、不低价内卷？',
  '怎么不靠熬夜搬货增加收入？',
  '怎么优化库存减少过期损耗？',
  '如何设计阶梯锁客模式、绑定食堂客户？'
]

const formatAnswer = (text) => {
  if (!text) return ''
  return text
    .replace(/\n/g, '<br>')
    .replace(/【([^】]+)】/g, '<strong style="color: #409EFF;">【$1】</strong>')
    .replace(/📌([^\n]*)/g, '<div style="background: #ECF5FF; padding: 8px; margin: 8px 0; border-radius: 4px;">📌$1</div>')
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

const loadSessions = async () => {
  try {
    sessions.value = await getAISessions()
  } catch { /* handled */ }
}

const selectSession = async (sessionId) => {
  currentSession.value = sessionId
  try {
    messages.value = await getAISession(sessionId)
    scrollToBottom()
  } catch { /* handled */ }
}

const newSession = () => {
  currentSession.value = null
  messages.value = []
}

const askSuggestion = async (question) => {
  inputQuestion.value = question
  await sendQuestion()
}

const sendQuestion = async () => {
  const question = inputQuestion.value.trim()
  if (!question || loading.value) return

  messages.value.push({ role: 'user', content: question })
  inputQuestion.value = ''
  loading.value = true
  scrollToBottom()

  try {
    const result = await aiAsk({
      question,
      session_id: currentSession.value || undefined
    })

    currentSession.value = result.session_id
    messages.value.push({ role: 'assistant', content: result.answer })

    scrollToBottom()
    loadSessions()
  } catch (e) {
    messages.value.push({
      role: 'assistant',
      content: '抱歉，我暂时无法回答这个问题。请稍后重试。'
    })
    scrollToBottom()
  } finally {
    loading.value = false
  }
}

watch(messages, () => {
  scrollToBottom()
}, { deep: true })

onMounted(() => {
  loadSessions()
})
</script>

<style scoped>
.ai-chat-container {
  height: calc(100vh - 140px);
}

.chat-main {
  display: flex;
  flex-direction: column;

  .chat-header {
    display: flex;
    align-items: center;
    gap: 10px;
    padding-bottom: 15px;
    border-bottom: 1px solid #ebeef5;
  }

  .chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 20px 0;
    min-height: 300px;
    max-height: calc(100vh - 320px);
  }

  .welcome-message {
    text-align: center;
    padding: 40px 20px;
    color: #606266;

    h2 { margin: 10px 0; }
    p { color: #909399; margin: 5px 0; }
  }

  .suggestion-list {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
    margin: 15px 0;

    .suggestion-tag {
      cursor: pointer;
      transition: all 0.2s;

      &:hover {
        background: #409EFF;
        color: #fff;
      }
    }
  }

  .message-row {
    display: flex;
    margin-bottom: 15px;
    gap: 10px;

    &.user {
      flex-direction: row-reverse;

      .message-content {
        background: #409EFF;
        color: #fff;
        border-radius: 12px 12px 0 12px;
        max-width: 70%;
      }
    }

    &.assistant {
      .message-content {
        background: #F5F7FA;
        border-radius: 12px 12px 12px 0;
        max-width: 80%;
      }
    }
  }

  .message-avatar { flex-shrink: 0; }

  .message-content {
    padding: 12px 16px;
    line-height: 1.7;

    .ai-answer {
      white-space: pre-wrap;

      :deep(strong) { display: inline; }
      :deep(div) { margin: 8px 0; }
    }

    .user-question {
      white-space: pre-wrap;
    }
  }

  .loading-dots {
    display: flex;
    gap: 4px;
    padding: 8px 0;

    span {
      width: 8px;
      height: 8px;
      background: #909399;
      border-radius: 50%;
      animation: bounce 1.4s infinite ease-in-out both;

      &:nth-child(1) { animation-delay: -0.32s; }
      &:nth-child(2) { animation-delay: -0.16s; }
    }
  }

  @keyframes bounce {
    0%, 80%, 100% { transform: scale(0); }
    40% { transform: scale(1); }
  }

  .chat-input {
    border-top: 1px solid #ebeef5;
    padding-top: 15px;
  }
}

.session-item {
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
  margin-bottom: 5px;

  &:hover { background: #F5F7FA; }
  &.active { background: #ECF5FF; }

  .session-preview {
    font-size: 13px;
    color: #303133;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }

  .session-time {
    font-size: 11px;
    color: #909399;
    margin-top: 5px;
  }
}
</style>
