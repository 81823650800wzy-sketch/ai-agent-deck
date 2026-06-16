cmake_minimum_required(VERSION 3.16)

# Exclude unused components to avoid GCC ICE issues
set(EXCLUDE_COMPONENTS esp_lcd)

set(EXTRA_COMPONENT_DIRS components)
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(ai_agent_deck)
