<template>
  <svg
    class="site-logo"
    viewBox="0 0 100 100"
    xmlns="http://www.w3.org/2000/svg"
    :role="decorative ? undefined : 'img'"
    :aria-label="decorative ? undefined : label"
    :aria-hidden="decorative ? 'true' : undefined"
  >
    <defs>
      <linearGradient :id="gradientId" x1="18%" y1="14%" x2="84%" y2="88%">
        <stop offset="0%" stop-color="#a7f3d0" />
        <stop offset="52%" stop-color="#34d399" />
        <stop offset="100%" stop-color="#059669" />
      </linearGradient>
      <radialGradient :id="glowId" cx="50%" cy="34%" r="70%">
        <stop offset="0%" stop-color="#bbf7d0" stop-opacity="0.46" />
        <stop offset="72%" stop-color="#34d399" stop-opacity="0" />
      </radialGradient>
      <filter :id="shadowId" x="-20%" y="-20%" width="140%" height="140%">
        <feDropShadow dx="0" dy="7" stdDeviation="5" flood-color="#022c22" flood-opacity="0.24" />
      </filter>
    </defs>

    <g v-if="plate">
      <rect x="8" y="8" width="84" height="84" rx="24" fill="#052e2b" />
      <rect x="8.5" y="8.5" width="83" height="83" rx="23.5" fill="none" stroke="#0f766e" stroke-opacity="0.28" />
      <circle cx="50" cy="41" r="34" :fill="`url(#${glowId})`" />
    </g>

    <g :filter="`url(#${shadowId})`">
      <path
        d="M 46 12 C 26 25 16 45 16 60 C 16 80 41 90 61 85 C 74 82 84 72 84 60 L 74 56 C 74 64 66 72 56 75 C 41 78 30 70 30 55 C 30 45 38 30 46 22 Z"
        :fill="`url(#${gradientId})`"
      />
      <path
        d="M 51 15 L 71 60 L 61 60 L 57 48 C 52 49.5 46 49.5 40 48 L 44 40 C 49 41.5 53 41.5 55 40 L 49 24 Z"
        :fill="`url(#${gradientId})`"
      />
    </g>
  </svg>
</template>

<script setup>
import { computed, useId } from "vue";

const props = defineProps({
  label: {
    type: String,
    default: "AlgoWiki logo",
  },
  decorative: {
    type: Boolean,
    default: false,
  },
  plate: {
    type: Boolean,
    default: false,
  },
});

const uid = useId();
const gradientId = computed(() => `site-logo-gradient-${uid}`);
const glowId = computed(() => `site-logo-glow-${uid}`);
const shadowId = computed(() => `site-logo-shadow-${uid}`);
</script>

<style scoped>
.site-logo {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
