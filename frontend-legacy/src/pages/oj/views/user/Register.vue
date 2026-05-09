<template>
  <div>
    <Form ref="formRegister" :model="formRegister" :rules="ruleRegister">
      <FormItem prop="username">
        <Input
          type="text"
          v-model="formRegister.username"
          :placeholder="$t('m.RegisterUsername')"
          size="large"
          @on-enter="handleRegister"
        >
          <Icon type="ios-person-outline" slot="prepend"></Icon>
        </Input>
      </FormItem>
      <FormItem prop="email">
        <Input
          v-model="formRegister.email"
          :placeholder="$t('m.Email_Address')"
          size="large"
          @on-enter="handleRegister"
        >
          <Icon type="ios-email-outline" slot="prepend"></Icon>
        </Input>
      </FormItem>
      <FormItem prop="password">
        <Input
          type="password"
          v-model="formRegister.password"
          :placeholder="$t('m.RegisterPassword')"
          size="large"
          @on-enter="handleRegister"
        >
          <Icon type="ios-locked-outline" slot="prepend"></Icon>
        </Input>
      </FormItem>
      <FormItem prop="passwordAgain">
        <Input
          type="password"
          v-model="formRegister.passwordAgain"
          :placeholder="$t('m.Password_Again')"
          size="large"
          @on-enter="handleRegister"
        >
          <Icon type="ios-locked-outline" slot="prepend"></Icon>
        </Input>
      </FormItem>
      <FormItem prop="captcha" style="margin-bottom: 10px">
        <div class="oj-captcha">
          <div class="oj-captcha-code">
            <Input
              v-model="formRegister.captcha"
              :placeholder="$t('m.Captcha')"
              size="large"
              @on-enter="handleRegister"
            >
              <Icon type="ios-lightbulb-outline" slot="prepend"></Icon>
            </Input>
          </div>
          <div class="oj-captcha-img">
            <Tooltip content="Click to refresh" placement="top">
              <img :src="captchaSrc" @click="getCaptchaSrc" />
            </Tooltip>
          </div>
        </div>
      </FormItem>
    </Form>
    <div class="footer">
      <div class="age-notice">
        만 14세 미만 아동은 직접 가입이 제한됩니다.<br />
        학교 수업용 계정이 필요한 경우 담당 선생님께 요청하세요.
      </div>
      <Checkbox v-model="ageConfirmed" class="age-checkbox">
        <span class="required-tag">*</span> 본인은 만 14세 이상입니다.
      </Checkbox>
      <Button
        type="primary"
        @click="handleRegister"
        class="btn"
        long
        :loading="btnRegisterLoading"
        :disabled="!ageConfirmed"
      >
        {{ $t("m.UserRegister") }}
      </Button>
      <Button type="ghost" @click="switchMode('login')" class="btn" long>
        {{ $t("m.Already_Registed") }}
      </Button>
    </div>
  </div>
</template>

<script>
import { mapGetters, mapActions } from "vuex";
import api from "@oj/api";
import { FormMixin } from "@oj/components/mixins";

export default {
  mixins: [FormMixin],
  mounted() {
    this.getCaptchaSrc();
  },
  data() {
    const CheckUsernameNotExist = (rule, value, callback) => {
      api.checkUsernameOrEmail(value, undefined).then(
        (res) => {
          if (res.data.data.username === true) {
            callback(new Error(this.$i18n.t("m.The_username_already_exists")));
          } else {
            callback();
          }
        },
        (_) => callback(),
      );
    };
    const CheckEmailNotExist = (rule, value, callback) => {
      api.checkUsernameOrEmail(undefined, value).then(
        (res) => {
          if (res.data.data.email === true) {
            callback(new Error(this.$i18n.t("m.The_email_already_exists")));
          } else {
            callback();
          }
        },
        (_) => callback(),
      );
    };
    const CheckPassword = (rule, value, callback) => {
      if (this.formRegister.password !== "") {
        // 对第二个密码框再次验证
        this.$refs.formRegister.validateField("passwordAgain");
      }
      callback();
    };

    const CheckAgainPassword = (rule, value, callback) => {
      if (value !== this.formRegister.password) {
        callback(new Error(this.$i18n.t("m.password_does_not_match")));
      }
      callback();
    };

    return {
      btnRegisterLoading: false,
      ageConfirmed: false,
      formRegister: {
        username: "",
        password: "",
        passwordAgain: "",
        email: "",
        captcha: "",
      },
      ruleRegister: {
        username: [
          { required: true, trigger: "blur" },
          { validator: CheckUsernameNotExist, trigger: "blur" },
        ],
        email: [
          { required: true, type: "email", trigger: "blur" },
          { validator: CheckEmailNotExist, trigger: "blur" },
        ],
        password: [
          { required: true, trigger: "blur", min: 6, max: 20 },
          { validator: CheckPassword, trigger: "blur" },
        ],
        passwordAgain: [
          { required: true, validator: CheckAgainPassword, trigger: "change" },
        ],
        captcha: [{ required: true, trigger: "blur", min: 1, max: 10 }],
      },
    };
  },
  methods: {
    ...mapActions(["changeModalStatus", "getProfile"]),
    switchMode(mode) {
      this.changeModalStatus({
        mode,
        visible: true,
      });
    },
    handleRegister() {
      if (!this.ageConfirmed) {
        this.$error("만 14세 이상 확인에 동의해주세요.");
        return;
      }
      this.validateForm("formRegister").then((valid) => {
        let formData = Object.assign({}, this.formRegister);
        delete formData["passwordAgain"];
        this.btnRegisterLoading = true;
        api.register(formData).then(
          (res) => {
            this.$success(this.$i18n.t("m.Thanks_for_registering"));
            this.switchMode("login");
            this.btnRegisterLoading = false;
          },
          (_) => {
            this.getCaptchaSrc();
            this.formRegister.captcha = "";
            this.btnRegisterLoading = false;
          },
        );
      });
    },
  },
  computed: {
    ...mapGetters(["website", "modalStatus"]),
  },
};
</script>

<style scoped lang="less">
.footer {
  overflow: auto;
  margin-top: 20px;
  margin-bottom: -15px;
  text-align: left;
  .btn {
    margin: 0 0 15px 0;
    &:last-child {
      margin: 0;
    }
  }
}
.age-notice {
  font-size: 13px;
  color: #e6a23c;
  margin-bottom: 15px;
  line-height: 1.6;
}
.age-checkbox {
  display: block;
  margin-bottom: 15px;
  font-size: 13px;
}
.required-tag {
  color: #ed4014;
  font-weight: bold;
}
</style>
