from utils.api.tests import APITestCase

from .models import AvatarItem


def blank(w, h):
    return "." * (w * h)


def painted(w, h, ch="i"):
    text = blank(w, h)
    return ch + text[1:]


def hat_data(**overrides):
    data = {"name": "빨간 비니", "slot": "hat", "variant": "top",
            "parts": {"head": painted(40, 36)}, "price": 40, "visible": False, "designer": ""}
    data.update(overrides)
    return data


class AvatarItemAdminAPITest(APITestCase):
    def setUp(self):
        self.url = self.reverse("avatar_item_admin_api")
        self.create_super_admin()

    def test_create_and_list(self):
        resp = self.client.post(self.url, data=hat_data())
        self.assertSuccess(resp)
        item = AvatarItem.objects.get()
        self.assertEqual(item.variant, "top")
        self.assertEqual(item.parts["head"][0], "i")
        resp = self.client.get(self.url)
        self.assertSuccess(resp)
        self.assertEqual([i["name"] for i in resp.data["data"]], ["빨간 비니"])

    def test_variant_defaults_to_first_choice(self):
        resp = self.client.post(self.url, data=hat_data(variant=""))
        self.assertSuccess(resp)
        self.assertEqual(AvatarItem.objects.get().variant, "top")

    def test_rejects_wrong_variant(self):
        self.assertFailed(self.client.post(self.url, data=hat_data(variant="pants")))
        # 종류가 없는 자리에 종류를 적어도 안 된다
        self.assertFailed(self.client.post(self.url, data=hat_data(slot="hair", variant="top")))

    def test_parts_must_match_slot(self):
        # 치마는 skirt 한 부위, 바지는 양 다리
        skirt = {"skirt": painted(26, 16)}
        self.assertSuccess(self.client.post(self.url, data=hat_data(slot="bottom", variant="skirt", parts=skirt)))
        self.assertFailed(self.client.post(self.url, data=hat_data(slot="bottom", variant="pants", parts=skirt)))
        legs = {"legL": painted(11, 16), "legR": blank(11, 16)}
        self.assertSuccess(self.client.post(self.url, data=hat_data(slot="bottom", variant="pants", parts=legs)))

    def test_rejects_wrong_size_or_letters(self):
        self.assertFailed(self.client.post(self.url, data=hat_data(parts={"head": "i" * 10})))
        bad = "#" + blank(40, 36)[1:]
        self.assertFailed(self.client.post(self.url, data=hat_data(parts={"head": bad})))

    def test_rejects_empty_drawing(self):
        self.assertFailed(self.client.post(self.url, data=hat_data(parts={"head": blank(40, 36)})))

    def test_rejects_blank_name(self):
        self.assertFailed(self.client.post(self.url, data=hat_data(name="   ")))

    def test_update_and_delete(self):
        self.client.post(self.url, data=hat_data())
        item = AvatarItem.objects.get()
        resp = self.client.put(self.url, data={**hat_data(price=99, visible=True), "id": item.id})
        self.assertSuccess(resp)
        item.refresh_from_db()
        self.assertEqual((item.price, item.visible), (99, True))
        self.assertSuccess(self.client.delete(self.url + f"?id={item.id}"))
        self.assertFalse(AvatarItem.objects.exists())

    def test_update_missing_item(self):
        self.assertFailed(self.client.put(self.url, data={**hat_data(), "id": 999}))

    def test_only_super_admin(self):
        for login in (self.create_admin, self.create_teacher, lambda: self.create_user("s", "s")):
            self.client.logout()
            login()
            # 관리자가 아니면 미들웨어가(login-required), 일반 관리자는 데코레이터가 막는다
            self.assertFailed(self.client.post(self.url, data=hat_data()))
            self.assertFailed(self.client.get(self.url))
        self.assertFalse(AvatarItem.objects.exists())
