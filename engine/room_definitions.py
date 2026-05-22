"""
Central repository for map layouts and room prototypes.
"""

ROOM_PROTOTYPES = {
    "chapter1_start": [
        "##########",
        "#........#",
        "#.B....R.#",
        "#....T...#",
        "#........#",
        "##########"
    ],
    "sanctuary_prototype": [
        "################################",
        "#..............................#",
        "#..............................#",
        "#.........############.........#",
        "#.........#..........#.........#",
        "#.........W..........#.........#",
        "#.........#..........#.........#",
        "#.........############.........#",
        "#..............................#",
        "#..............................#",
        "################################"
    ]
}

# Supplemental entity data for prototypes
# Mapping: room_id -> (x, y) -> data_dict
ENTITY_MANIFEST = {
    "sanctuary_prototype": {
        (10, 5): {
            "target": "outside",
            "name": "The Chronicle",
            # spawn_x and spawn_y would be set here too
        }
    }
}
