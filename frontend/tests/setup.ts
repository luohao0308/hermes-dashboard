import { config } from '@vue/test-utils'
import i18n from '../src/i18n'

// Force en-US locale for consistent test assertions
i18n.global.locale.value = 'en-US'

// Register i18n plugin globally so components using useI18n() work in tests
config.global.plugins = [i18n]
