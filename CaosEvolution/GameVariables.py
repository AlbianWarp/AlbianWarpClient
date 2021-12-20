from CaosEvolution import CI


class StringGameVariable:
    def __init__(self, variable_name):
        self.variable_name = variable_name

    def _set_str_game_variable(self, value):
        CI.ExecuteCaos(f'sets game "{self.variable_name}" "{value}"')

    def _get_str_game_variable(self):
        return str(
            CI.ExecuteCaos(f'outs game "{self.variable_name}"').Content.strip("\x00")
        )

    Value = property(_get_str_game_variable, _set_str_game_variable)


class IntegerGameVariable:
    def __init__(self, variable_name):
        self.variable_name = variable_name

    def _set_int_game_variable(self, value):
        CI.ExecuteCaos(f'setv game "{self.variable_name}" {value}')

    def _get_int_game_variable(self):
        return int(
            CI.ExecuteCaos(f'outv game "{self.variable_name}"').Content.strip("\x00")
        )

    Value = property(_get_int_game_variable, _set_int_game_variable)


class StringEngineVariable:
    def __init__(self, variable_name):
        self.variable_name = variable_name

    def _set_str_eame_variable(self, value):
        CI.ExecuteCaos(f'sets eame "{self.variable_name}" "{value}"')

    def _get_str_eame_variable(self):
        return str(
            CI.ExecuteCaos(f'outs eame "{self.variable_name}"').Content.strip("\x00")
        )

    Value = property(_get_str_eame_variable, _set_str_eame_variable)


class IntegerEngineVariable:
    def __init__(self, variable_name):
        self.variable_name = variable_name

    def _set_int_eame_variable(self, value):
        CI.ExecuteCaos(f'setv eame "{self.variable_name}" {value}')

    def _get_int_eame_variable(self):
        return int(
            CI.ExecuteCaos(f'outv eame "{self.variable_name}"').Content.strip("\x00")
        )

    Value = property(_get_int_eame_variable, _set_int_eame_variable)


# region game variables
# Game Variables used by AlbianWarp
# Original game variables start with the prefix "game_" followed by their name.
# Variables used exclusively by AlbianWarp start with the prefix "game_aw_"

# Online Status Variables

# the original online status variable possible values are "offline", "pending", "online", also set by AW for compatibillity reason
game_status = StringGameVariable("status")
# the online status variable used by AW possible values are "offline" and "online"
game_aw_status = StringGameVariable("aw_status")
# the original username variable, it stores the username of the logged in user, also set by AW for compatibillity reason
game_user_of_this_world = StringGameVariable("user_of_this_world")
# online connectivity indicator variable
game_aw_online_indicator = IntegerGameVariable("aw_online_indicator")
# endregion

# region engine Variables
# version of the ingame CAOS modifications
eame_aw_mod_version = StringEngineVariable("aw_mod_version")
# endregion
