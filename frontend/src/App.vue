<template>
  <div class="app-shell" :class="`app-shell--${theme.currentTheme}`">
    <TopNav />
    <ToastStack />
    <ChatAssistantLauncher />
    <main class="page-shell" :class="{ 'page-shell--flush': isHomeLayout }">
      <RouterView />
    </main>
    <AnnouncementModal
      :visible="showAnnouncement"
      :announcement="activeAnnouncement"
      @close="dismissAnnouncement"
    />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted } from "vue";
import { RouterView } from "vue-router";
import { useRoute } from "vue-router";
import AnnouncementModal from "./components/AnnouncementModal.vue";
import ChatAssistantLauncher from "./components/ChatAssistantLauncher.vue";
import TopNav from "./components/TopNav.vue";
import ToastStack from "./components/ToastStack.vue";
import { useAnnouncementPopup } from "./composables/useAnnouncementPopup";
import { useScrollGradientTheme } from "./composables/useScrollGradientTheme";
import { useAuthStore } from "./stores/auth";
import { useThemeStore } from "./stores/theme";

const route = useRoute();
const auth = useAuthStore();
const theme = useThemeStore();
const isHomeLayout = computed(() => route.name === "home");
const { showAnnouncement, activeAnnouncement, dismissAnnouncement } = useAnnouncementPopup(auth);

theme.init();
useScrollGradientTheme();

function handleInvalidToken() {
  auth.clearAuth();
}

onMounted(() => {
  window.addEventListener("algowiki:auth-invalid", handleInvalidToken);
});

onBeforeUnmount(() => {
  window.removeEventListener("algowiki:auth-invalid", handleInvalidToken);
});
</script>
