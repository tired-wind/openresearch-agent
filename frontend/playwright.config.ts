import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./e2e',timeout:90000,workers:1,use:{baseURL:'http://127.0.0.1:3018',channel:process.env.CI ? undefined : 'chrome',headless:true,viewport:{width:1440,height:1100}},reporter:'list'});
