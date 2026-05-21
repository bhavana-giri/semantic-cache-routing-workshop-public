/**
 * Workshop Configuration
 *
 * Customize this file for your workshop. Add, remove, or modify panels
 * to match your workshop's needs.
 *
 * Sidebar fields:
 *   id      - Unique identifier for the sidebar
 *   name    - Display name shown in the panel header and menu
 *   path    - URL path to the service (e.g., '/docs/')
 *   icon    - Font Awesome icon class (e.g., 'fa-book')
 *
 * Panel fields:
 *   id      - Unique identifier for the panel
 *   name    - Display name shown in the panel header and menu
 *   path    - URL path to the service (e.g., '/vscode/')
 *   icon    - Font Awesome icon class (e.g., 'fa-code')
 *   visible - Whether the panel is visible by default (true/false)
 */

const config = {
  // Workshop title displayed in the header
  title: "E-Commerce Support Semantic Cache Workshop",

  // Sidebar panel (always visible on the left)
  sidebar: {
    id: 'instructions',
    name: 'Instructions',
    path: '/docs/',
    icon: 'fa-book'
  },

  // Right-side panels (can be shown/hidden/maximized)
  panels: [
    {
      id: 'vscode',
      name: 'Code',
      path: '/vscode/',
      icon: 'fa-code',
      visible: true
    },
    {
      id: 'app',
      name: 'Support Console',
      path: '/app/',
      icon: 'fa-rocket',
      visible: true
    },
    {
      id: 'terminal',
      name: 'Terminal',
      path: '/terminal/',
      icon: 'fa-terminal',
      visible: false
    },
    {
      id: 'redisinsight',
      name: 'Redis Insight',
      path: '/redisinsight/',
      icon: 'fa-database',
      visible: false
    }
  ]
};
