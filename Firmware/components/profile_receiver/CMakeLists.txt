idf_component_register(
    SRCS "profile_receiver.c"
    INCLUDE_DIRS "include"
    REQUIRES bt nvs_flash json
)
