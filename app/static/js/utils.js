import { CATEGORY_THEME_MAP } from './config.js';

export function getThemesFromCategories(categories = []) {
    if (!categories) return [];
    return categories.map(cat => CATEGORY_THEME_MAP[cat]).filter(Boolean);
}

export function findMainTheme(categories = []) {
    for (const cat of categories) {
        const theme = CATEGORY_THEME_MAP[cat];
        if (theme) return theme;
    }
    return 'default';
}