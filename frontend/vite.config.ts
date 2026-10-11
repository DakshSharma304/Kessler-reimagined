import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
export default defineConfig({plugins:[react()],optimizeDeps:{include:['@react-three/fiber','@react-three/drei','three']},server:{port:5173,strictPort:true},build:{target:'es2022'},test:{environment:'jsdom',include:['src/**/*.test.{ts,tsx}'],restoreMocks:true}});
