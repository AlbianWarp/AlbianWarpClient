from CaosEvolution import CI
import logging
import json
import re


class AgentBuilder:
    def __init__(self, family, genus, species, data):
        self.family = family
        self.genus = genus
        self.species = species
        self.data = data
        self.caos = ""

    def inject(self):
        self.caos += 'new: simp %s %s %s "blnk" 1 0 0\n' % (
            self.family,
            self.genus,
            self.species,
        )
        for key, value in self.data.items():
            if type(value) in [float, int]:
                self.caos += f'setv name "{key}" {value}\n'
            if type(value) == str:
                self.caos += 'sets name "%s" "%s"\n' % (key, value.replace("\n", r"\n"))
        return CI.ExecuteCaos(self.caos)


def enumAgents(family, genus, species):
    tmp = list()
    result = CI.ExecuteCaos(f'enum {family} {genus} {species} outv unid outs "|" next')
    if result.Content.strip("|\x00").strip() != "":
        for unid in result.Content.strip("|\x00").split("|"):
            logging.debug(f"enumerated {family} {genus} {species}  - unid: {unid}")
            tmp.append(Agent(unid))
    return tmp


class Agent:
    def __init__(self, unique_id):
        self.unid = unique_id

    @property
    def species(self):
        return int(
            CI.ExecuteCaos(f"targ agnt {self.unid} outv spcs").Content.strip("\x00")
        )

    @property
    def family(self):
        return int(
            CI.ExecuteCaos(f"targ agnt {self.unid} outv fmly").Content.strip("\x00")
        )

    @property
    def genus(self):
        return int(
            CI.ExecuteCaos(f"targ agnt {self.unid} outv gnus").Content.strip("\x00")
        )

    def Kill(self):
        result = CI.ExecuteCaos(f"kill agnt {self.unid}")
        if not result.Success:
            raise Exception(f"Could not Kill Agent!\n {result.Content}")

    def GetOV(self, xx):
        if xx not in range(0, 100):
            raise Exception("OV must be vetween 00 and 99!")
        result = CI.ExecuteCaos("targ agnt %s outv type ov%02d" % (self.unid, xx))
        if int(result.Content.strip("\x00")) in [0, 1]:
            return int(
                CI.ExecuteCaos(
                    "targ agnt %s outv ov%02d" % (self.unid, xx)
                ).Content.strip("\x00")
            )
        elif int(result.Content.strip("\x00")) in [2]:
            return CI.ExecuteCaos(
                "targ agnt %s outs ov%02d" % (self.unid, xx)
            ).Content.strip("\x00")

    def SetOV(self, xx, value):
        if xx not in range(0, 100):
            raise Exception("OV must be vetween 00 and 99!")
        if type(value) in [int, float]:
            CI.ExecuteCaos("targ agnt %s setv ov%02d %s" % (self.unid, xx, value))
        elif type(value) == str:
            CI.ExecuteCaos('targ agnt %s sets ov%02d "%s"' % (self.unid, xx, value))

    def GetNAME(self, xx):
        result = CI.ExecuteCaos(f'targ agnt {self.unid} outv type name "{xx}"')
        if int(result.Content.strip("\x00")) in [0, 1]:
            return int(
                CI.ExecuteCaos(f'targ agnt {self.unid} outv name "{xx}"').Content.strip(
                    "\x00"
                )
            )
        elif int(result.Content.strip("\x00")) in [2]:
            return CI.ExecuteCaos(
                f'targ agnt {self.unid} outs name "{xx}"'
            ).Content.strip("\x00")

    def SetNAME(self, xx, value):
        if type(value) in [int, float]:
            CI.ExecuteCaos(f'targ agnt {self.unid} setv name "{xx}" {value}')
        elif type(value) == str:
            CI.ExecuteCaos(f'targ agnt {self.unid} sets name "{xx}" "{value}"')

    @property
    def _json(self):
        unclean_json = CI.ExecuteCaos(
            r'targ agnt %s sets va00 "" outs "{" loop namn va00  doif va00 ne "" outs "\"" outs va00 outs "\": " setv va10 type name va00 doif va10 eq 2 outx name va00  elif va10 lt 2 outv name va00 endi outs "," endi untl va00 eq "" outs "}"'
            % self.unid
        ).Content.strip("\x00")
        unclean_json = re.sub(",}$", "}", unclean_json)
        unclean_json = unclean_json.replace("\\'", "'")
        return unclean_json

    @property
    def dict(self):
        print(self._json)
        return json.loads(self._json)
